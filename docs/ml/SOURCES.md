# Evidence and dataset provenance

Checked 2026-10-17. Prediction outputs are hypotheses, not official road closures.

- SpaceNet 8: https://spacenet.ai/sn8-challenge/ — Louisiana Hurricane Ida (2021), Germany flooding (2021), CC BY-SA 4.0. Individual GeoTIFFs and GeoJSON annotations accessible without authentication from https://spacenet-dataset.s3.amazonaws.com/spacenet/SN8_floods/ . Do not download whole tarballs on this nearly full laptop. Images and label pairs must stay in one spatial split. Full flood evaluation needs pre/post alignment and properly annotated flooded-road labels.
- Official baseline/code: https://github.com/SpaceNetChallenge/SpaceNet8 . Research: https://openaccess.thecvf.com/content/CVPR2022W/EarthVision/papers/Hansch_SpaceNet_8_-_The_Detection_of_Flooded_Roads_and_Buildings_CVPRW_2022_paper.pdf . No external baseline code copied in this change.
- NVIDIA baseline model: https://huggingface.co/nvidia/segformer-b0-finetuned-ade-512-512 . Published before hackathon cutoff. Model license metadata is `other`; review upstream terms before weight redistribution. Used for local inference, no weights republished. Processor loaded from same pinned revision.
- Flood-specific candidate https://huggingface.co/rbh227/floodnet-segformer has class 3 road flooded, 64,002,250 parameters and no model card/license in repository metadata. Not downloaded or used; training/preprocessing provenance and licensing unresolved.
- NC source metadata: https://services.gis.nc.gov/secure/rest/services/Imagery/Orthoimagery_Helene_2025/ImageServer?f=pjson . Source-native CRS EPSG:6543, six-inch imagery, 13 counties. Description explicitly says spring 2025, leaf-off and no unusual flooding. Swannanoa export requested bounding box [-82.323,35.603,-82.313,35.613], EPSG:4326, 512x512, RGB bands. This export is resampled and does not retain six-inch effective resolution. Response extent and service metadata saved under ml/artifacts. Exact tile capture date unverified. Source rights must be checked before publishing imagery.
- NOAA immediate-response alternative: https://www.fisheries.noaa.gov/inport/item/73570 and https://storms.ngs.noaa.gov/storms/helene/index.html . A small Chimney Rock Main Street sample from NOAA layer 20241007a_RGB was downloaded, georeferenced from its documented XYZ grid, and processed separately. Acquisition day is October 7, 2024; exact flight time is unverified. No Helene accuracy is claimed. See PITCH_PROVENANCE.md.
- Nemotron https://build.nvidia.com/nvidia/nemotron-3.5-lightning-30b-a3b/modelcard — 30B total, 3B active, text input/output, release August 11 2026.
- Brev https://docs.nvidia.com/brev/getting-started/quickstart and https://docs.nvidia.com/brev/cli/search-discovery . Local CLI is official v0.6.337 binary, not system-installed.
- Red Hat https://docs.redhat.com/en/documentation/red_hat_ai_inference_server/ — no deployed integration verified.
- NeMo Gym https://docs.nvidia.com/nemo/gym/ and https://github.com/NVIDIA-NeMo/Gym — official v0.6.0 resource-server integration and protocol tests verified; no real LLM rollouts or improvement measured. See NEMO_GYM.md.

## Pitch statistics

See [PITCH_PROVENANCE.md](PITCH_PROVENANCE.md) for qualified primary-source figures, people/customer/site units, geography and direct-fetch limits.
