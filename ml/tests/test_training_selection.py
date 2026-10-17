import json
import sys
from types import SimpleNamespace

import pytest
import torch
from PIL import Image

from ml.vision import train


def test_existing_evidence_is_protected(tmp_path):
    evidence = tmp_path / "final_metrics.json"
    evidence.write_text("existing evidence")
    with pytest.raises(ValueError, match="new or empty"):
        train.prepare_output(tmp_path)
    assert evidence.read_text() == "existing evidence"


@pytest.mark.parametrize("score", [None, float("nan"), float("inf"), -float("inf")])
def test_invalid_validation_cannot_select_checkpoint(score):
    assert not train.improved_validation_score({"f1": score}, -float("inf"))


@pytest.mark.parametrize("mode", ["normal", "skip_test", "time_bound", "batched"])
def test_best_epoch_restored_and_test_evaluated_once(monkeypatch, tmp_path, mode):
    image = tmp_path / "image.png"
    mask = tmp_path / "mask.png"
    Image.new("RGB", (1, 1)).save(image)
    Image.new("L", (1, 1), color=1).save(mask)
    rows = [dict(image=str(image), mask=str(mask), split=split, spatial_group=split)
            for split in ["train", "validation", "test"]]
    if mode == "batched":
        rows.insert(0, dict(rows[0]))
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps(rows))
    out = tmp_path / "run"
    calls = []

    class Model(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.weight = torch.nn.Parameter(torch.tensor(0.0))
            self.segformer = torch.nn.Linear(1, 1)
            self.config = SimpleNamespace()

        def forward(self, **batch):
            calls.append((self.training, float(self.weight.detach())))
            # Epoch 1 is perfect; epoch 2 predicts the wrong class.
            positive = float(self.weight.detach()) < 1.5
            logits = torch.tensor([[[[0.0]], [[1.0 if positive else -1.0]]]])
            return SimpleNamespace(loss=-self.weight, logits=logits.repeat(batch["pixel_values"].shape[0],1,1,1))

        def save_pretrained(self, destination):
            destination.mkdir()
            (destination / "config.json").write_text("{}")
            torch.save(self.state_dict(), destination / "pytorch_model.bin")

    model = Model()

    class Processor:
        def __init__(self, **kwargs):
            pass

        def __call__(self, **kwargs):
            return {"pixel_values": torch.zeros((1, 3, 1, 1)),
                    "labels": torch.ones((1, 1, 1), dtype=torch.long)}

        def save_pretrained(self, destination):
            pass

    monkeypatch.setattr(train.SegformerForSemanticSegmentation, "from_pretrained", lambda *a, **k: model)
    monkeypatch.setattr(train, "SegformerImageProcessor", Processor)
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    monkeypatch.setattr(torch.backends.mps, "is_available", lambda: False)
    monkeypatch.setattr(torch.optim, "AdamW", lambda parameters, **kwargs: torch.optim.SGD(parameters, lr=1.0))
    extra = ["--device", "cpu", "--threads", "1", "--freeze-backbone", "--native-tile-inference", "--save-baseline-model"]
    if mode == "skip_test":
        extra += ["--skip-test"]
    if mode == "batched":
        extra += ["--batch-size", "2"]
    if mode == "time_bound":
        ticks = iter(range(100))
        monkeypatch.setattr(train.time, "monotonic", lambda: next(ticks))
        extra += ["--max-seconds", "5"]
    monkeypatch.setattr(sys, "argv", ["train", "--manifest", str(manifest), "--output", str(out), "--epochs", "2"] + extra)
    train.main()

    assert float(model.weight.detach()) == 1.0
    assert all(not p.requires_grad for p in model.segformer.parameters())
    assert model.config.sosora_tile_size == 256
    assert model.config.requires_road_roi is True
    assert (out / "baseline_model" / "pytorch_model.bin").is_file()
    expected = [(False, 0.0), (True, 0.0), (False, 1.0)]
    if mode != "time_bound":
        expected += [(True, 1.0), (False, 2.0)]
    if mode not in {"skip_test", "time_bound"}:
        expected += [(False, 1.0)]
    assert calls == expected
    metrics = json.loads((out / "final_metrics.json").read_text())
    if mode in {"skip_test", "time_bound"}:
        assert metrics["status"] == "not_evaluated"
        assert "f1" not in metrics
    else:
        assert metrics["f1"] == 1.0
    assert metrics["selected_epoch"] == 1
    metadata = json.loads((out / "run_metadata.json").read_text())
    assert metadata == json.loads((out / "model" / "run_metadata.json").read_text())
    assert metadata["label_map"]["0"] == "non_flooded_road"
    assert metadata["requires_road_roi"] is True
    assert metadata["native_tile_size"] == 256
    assert metadata["training_resolution"] == {"height": 256, "width": 256}
    assert metadata["checkpoint_id"].startswith("sha256:")
    config = json.loads((out / "evaluation_config.json").read_text())
    assert [row["train_loss"] for row in config["history"]] == ([0.0, None] if mode == "time_bound" else [0.0, -1.0])
    assert all("loss" in row["validation"] for row in config["history"] if row["validation"] is not None)
    assert metadata["timing"]["stopped_for_time"] == (mode == "time_bound")
    if mode == "batched":
        assert [row["training_samples"] for row in config["history"]] == [2, 2]
    assert json.loads((out / "baseline_metrics.json").read_text())["metrics"] is None
