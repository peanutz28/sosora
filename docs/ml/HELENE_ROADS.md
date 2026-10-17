# Helene-region independent road ROI

`data/manifests/helene_road_demo.json` registers `helene_swannanoa_roads_spring2025` against the existing georeferenced image. It is an **unlabeled transfer demo**, not a validation set. Spring 2025 imagery shows the recovery period, not immediate Hurricane Helene storm conditions. No flood labels or visual flood judgments were used to create this ROI.

## Source and construction

Official [NCDOT State Maintained Roads service, layer 0](https://gis11.services.ncdot.gov/arcgis/rest/services/NCDOT_StateMaintainedRoadsQtr/MapServer/0). NCDOT describes this as state-maintained roads from its Roads and Highways system, publication June 28, 2026. Its native service CRS is EPSG:2264 (feet). The saved query requests GeoJSON in EPSG:4326 only for the image bounding box: longitude -82.323 to -82.313, latitude 35.603 to 35.613.

Retrieved October 17, 2026: 23 features, 37,279 bytes. Geometry is independently transformed into metric UTM zone 17N (EPSG:32617), buffered **3 metres each side**, then transformed into image CRS and rasterized with the exact original affine transform and 512×512 grid. Pixel-center rasterization yields 5,808 road pixels (2.216%). Approximate pixel size is 1.80×2.19 metres. The buffer is a corridor convention, not a measured pavement width.

`ml/artifacts/helene_road_demo/` contains the original source GeoJSON, service metadata, provenance with full query/hash/date/CRS/grid registration, and matching PNG and georeferenced TIFF masks. ROI values are 0 outside roads, 1 inside. No flood state is encoded.

## Reproduction and integration

From repository root, using existing dependencies:

```sh
ml/.venv312/bin/python scripts/ml/prepare_helene_roads.py
```

The script refuses existing output paths to preserve evidence. Current artifacts already exist; do not rerun over them. Configure the inference service's image manifest to this distinct manifest and request image ID `helene_swannanoa_roads_spring2025`. It supplies `road_roi_path` required by flood inference. No model prediction has been run by this preparation step.

## Limits

- Roads published in June 2026 may differ from the spring 2025 scene. This is not a historical road inventory.
- State-maintained roads omit some municipal/private roads; the ROI is incomplete.
- Independent vector/image georegistration can contain residual offsets.
- Flood predictions on this scene have no independent accuracy measurement, and neither flood extent nor road passability is verified.
- NCDOT service copyright is “NCDOT GIS Unit.” Public service accessibility does not establish redistribution rights; verify imagery/road terms before publishing data. This local demo does not publish it.
