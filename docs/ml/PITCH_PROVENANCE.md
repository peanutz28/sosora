# Pitch facts and imagery provenance

Checked October 17, 2026. Use the following qualified wording; counts measure different things and dates/geographies matter.

| Topic | Defensible wording | Primary source and limits |
|---|---|---|
| Road infrastructure | By November 1, 2024 NCDOT had identified **more than 8,100 damage sites** involving roads, bridges and culverts in western North Carolina. | [NCDOT November1 release](https://www.ncdot.gov/news/press-releases/Pages/2024/2024-11-01-ncdot-relief-efforts-helene-western-nc.aspx). Locations/sites, not 8,100 distinct destroyed roads or bridges. |
| High-water rescues | **At least 2,700 people** were rescued from high water across the southeastern United States. | [NHC Helene report](https://www.nhc.noaa.gov/data/tcr/AL092024_Helene.pdf), p19, revised April8,2025. People, not rescue operations; not exclusively North Carolina. |
| Electricity | An estimated **7.4 million electricity customers** lost power cumulatively September 26–28, 2024; simultaneous peak was about **4.79 million**. | [NHC Helene report](https://www.nhc.noaa.gov/data/tcr/AL092024_Helene.pdf), p19. Customer accounts, not people; cumulative versus simultaneous counts must remain distinct. |
| Cell sites | Around **74.3% of cell sites** were out in the designated **21-county North Carolina disaster-reporting area**, September 28 snapshot at9 am EDT. | [FCC September 28 report](https://docs.fcc.gov/public/attachments/DOC-405893A1.pdf). Direct fetch returned 403 during independent research; exact passage was not independently retrieved in this environment. FCC September 29 report corroborates the prior 74.3% figure while reporting 66.4% then; [mirrored September 29 report](https://wirelessestimator.com/wp-content/uploads/2024/09/Hurricane.Helene.Cell_.Tower_.Status.pdf), p16. Mirror is corroboration, not the primary hosting domain. Do not call this statewide or current. |

## Imagery: three different sources and time periods

**SpaceNet8 Louisiana:** Hurricane Ida2021 training, validation and reused-four-tile evaluation. The frozen new Germany subset is a different2021 flood event. Neither is Hurricane Helene. Exact tile capture dates remain unverified. [Official dataset and license](https://spacenet.ai/sn8-challenge/).

**NC Helene Orthoimagery2025:** spring 2025 recovery imagery across 13 counties, source resolution six inches. Existing Swannanoa 512px export is resampled and does not preserve that effective resolution. [NCOneMap item](https://www.nconemap.gov/maps/06367a1aa3c044b890ca21cdbb2804e2/about); [machine-readable item metadata](https://www.arcgis.com/sharing/rest/content/items/06367a1aa3c044b890ca21cdbb2804e2?f=json). The metadata explicitly says processing may alter individual pixel values and discourages detailed pixel-value image analysis; it favors visual interpretation/general mapping. Consequently our segmentation is an exploratory transfer visualization, not validated radiometric analysis. Source service also says no unusual flooding at acquisition. Do not present these positives as evidence of September 2024 flood conditions or verified damage.

**NOAA NGS post-storm response:** western North Carolina imagery was collected **October 5–8, 2024**. September dates in the same catalog identify Florida coverage, not the NC hero location. [NOAA acquisition-day/location list](https://oceanservice.noaa.gov/news/sep24/ngs-storm-imagery-helene.html). October 7 includes Chimney Rock. [Official viewer](https://storms.ngs.noaa.gov/storms/helene/index.html), [layer catalog](https://storms.ngs.noaa.gov/storms/helene/services/index.json). Dated layers provide acquisition-day provenance; exact flight time/pixel dates require detailed metadata. Mosaic tiles are processed imagery, not guaranteed raw sensor values. NOAA describes imagery as informational/planning data without accuracy/completeness guarantees. Do not assume a license from the mixed basemap's third-party notice; preserve attribution and inspect the actual selected layer before any redistribution. Nothing was published here.

## Model evidence must remain qualified

The reused Louisiana F1 **0.674** is not a pristine holdout; earlier results/images informed diagnosis. The frozen label-blind Germany six-tile result is F1 **0.466**, with substantial false alarms/misses. Neither measures Helene accuracy, road closure correctness, passability or rescue-route safety. See [external evaluation](FROZEN_EXTERNAL_EVALUATION.md).

## Downloaded NOAA example

A four-tile October 7, 2024 NOAA mosaic covering Chimney Rock Main Street is now prepared and processed separately. Image ID `noaa_chimney_rock_20241007`; manifest `data/manifests/noaa_chimney_mainst_20241007.json`; provenance `ml/artifacts/noaa_chimney_mainst_20241007/provenance.json`. Only118,060 bytes were downloaded for the usable sample and road query. Its 512×512 EPSG3857 grid comes from documented XYZ tile coordinates, around0.49metre ground pixels at this latitude. Exactflighttime is unverified.

The unchanged model produced27 flooded-road and3 non-flooded-road polygons at threshold0.5, all unverified. There is no flood ground truth, quantitative accuracy, closure status, or safe-route claim. Road ROI uses June2026 NCDOT geometry, a temporal mismatch. Inference/overlay evidence is in `ml/artifacts/demo_noaa_chimney_20241007/`. The first wooded candidate had no NCDOT roads; its failed preparation is preserved in `ml/artifacts/noaa_chimney_20241007/failure.json` and no model inference ran on it.
