# Evaluation: Gemma reading street photos from Mainz, Germany

40 Mapillary photos, labelled by hand on the labelling page before looking at Gemma's answers.
Gemma runs locally through Ollama on an RTX 5060 laptop GPU (8 GB).

## Accuracy per question

| Question | Always "no" | gemma4:e4b | gemma4:e2b |
|---|---|---|---|
| seat | 92% | 95% (38/40) | 95% (38/40) |
| steps | 100% | 60% (24/40) | 98% (39/40) |
| broken_surface | 100% | 100% (40/40) | 100% (40/40) |
| shade | 95% | 35% (14/40) | 45% (18/40) |

## Finding places to sit

| Who | Accuracy | Seats it named that were real (precision) | Real seats it found (recall) | False seats | Missed seats |
|---|---|---|---|---|---|
| gemma4:e4b | 95% | 67% | 67% | 1 | 1 |
| gemma4:e2b | 95% | 100% | 33% | 0 | 2 |
| Map (bench within 15 m) | 85% | 20% | 33% | 4 | 2 |

## Speed and reliability

| Model | Usable answers | Median seconds per photo | Mean |
|---|---|---|---|
| gemma4:e4b | 40/40 | 0.93 | 1.19 |
| gemma4:e2b | 40/40 | 0.6 | 0.87 |

## Every mistake

### gemma4:e4b

| Photo | Question | Gemma said | Truth | Gemma's note |
|---|---|---|---|---|
| [1000891198977675](https://www.mapillary.com/app/?pKey=1000891198977675) | shade | yes | no | The immediate area near the camera is an open grassy field with no visible seating. |
| [1011607371182857](https://www.mapillary.com/app/?pKey=1011607371182857) | shade | yes | no | No clear seating options are visible in the immediate foreground area. |
| [1084284310213353](https://www.mapillary.com/app/?pKey=1084284310213353) | shade | yes | no | No visible seating options are clearly present near the camera within the immediate vicinity. |
| [1133642561990254](https://www.mapillary.com/app/?pKey=1133642561990254) | steps | yes | no | The immediate area near the camera has a raised curb and no visible seating. |
| [1133642561990254](https://www.mapillary.com/app/?pKey=1133642561990254) | shade | yes | no | The immediate area near the camera has a raised curb and no visible seating. |
| [1270132498155474](https://www.mapillary.com/app/?pKey=1270132498155474) | shade | yes | no | No clear seating options are visible in the immediate foreground area. |
| [1287583996406352](https://www.mapillary.com/app/?pKey=1287583996406352) | seat | yes | no | There is a visible bench near the left side of the path. |
| [1287583996406352](https://www.mapillary.com/app/?pKey=1287583996406352) | shade | yes | no | There is a visible bench near the left side of the path. |
| [1320968576170587](https://www.mapillary.com/app/?pKey=1320968576170587) | shade | yes | no | No clear seating options are visible in the immediate foreground area. |
| [1353833989490796](https://www.mapillary.com/app/?pKey=1353833989490796) | shade | yes | no | The immediate area is an open grassy field with no visible seating options. |
| [1386509323208868](https://www.mapillary.com/app/?pKey=1386509323208868) | steps | yes | no | There are no visible benches or seating areas immediately near the camera. |
| [1386509323208868](https://www.mapillary.com/app/?pKey=1386509323208868) | shade | yes | no | There are no visible benches or seating areas immediately near the camera. |
| [1398111569013702](https://www.mapillary.com/app/?pKey=1398111569013702) | shade | yes | no | No visible seating options are present in the immediate foreground area. |
| [1436760738496985](https://www.mapillary.com/app/?pKey=1436760738496985) | shade | yes | no | The immediate foreground is a paved area with shadows, but no visible seating is present. |
| [1489099005599085](https://www.mapillary.com/app/?pKey=1489099005599085) | steps | yes | no | The immediate area near the camera has a curb and no visible seating options. |
| [1519398533522093](https://www.mapillary.com/app/?pKey=1519398533522093) | shade | yes | no | No visible seating options are present in the immediate foreground area. |
| [1534806274732060](https://www.mapillary.com/app/?pKey=1534806274732060) | steps | yes | no | The immediate area near the camera shows a curb and no visible seating options. |
| [1534806274732060](https://www.mapillary.com/app/?pKey=1534806274732060) | shade | yes | no | The immediate area near the camera shows a curb and no visible seating options. |
| [1621064212647976](https://www.mapillary.com/app/?pKey=1621064212647976) | shade | yes | no | The immediate foreground shows shadows from trees, but no visible seating options are present. |
| [1710874073259089](https://www.mapillary.com/app/?pKey=1710874073259089) | shade | yes | no | No clear seating options are visible in the immediate foreground area. |
| [1740307813796316](https://www.mapillary.com/app/?pKey=1740307813796316) | shade | yes | no | The immediate area near the camera shows a path shaded by a large tree, but no visible seating. |
| [1900133340677216](https://www.mapillary.com/app/?pKey=1900133340677216) | steps | yes | no | The immediate area near the camera lacks any visible seating options for passers-by. |
| [1900133340677216](https://www.mapillary.com/app/?pKey=1900133340677216) | shade | yes | no | The immediate area near the camera lacks any visible seating options for passers-by. |
| [1927059791560432](https://www.mapillary.com/app/?pKey=1927059791560432) | shade | yes | no | There are no visible benches or seating areas immediately near the camera. |
| [2025483165029194](https://www.mapillary.com/app/?pKey=2025483165029194) | steps | yes | no | There is a raised concrete curb separating the path from the road, but no visible seating. |
| [2025483165029194](https://www.mapillary.com/app/?pKey=2025483165029194) | shade | yes | no | There is a raised concrete curb separating the path from the road, but no visible seating. |
| [2045494862743885](https://www.mapillary.com/app/?pKey=2045494862743885) | steps | yes | no | There is a raised curb separating the road from the sidewalk, but no visible seating. |
| [2045494862743885](https://www.mapillary.com/app/?pKey=2045494862743885) | shade | yes | no | There is a raised curb separating the road from the sidewalk, but no visible seating. |
| [25284584147904790](https://www.mapillary.com/app/?pKey=25284584147904790) | steps | yes | no | There are no visible benches or seating areas immediately near the camera. |
| [25284584147904790](https://www.mapillary.com/app/?pKey=25284584147904790) | shade | yes | no | There are no visible benches or seating areas immediately near the camera. |
| [4360182620881442](https://www.mapillary.com/app/?pKey=4360182620881442) | steps | yes | no | No clear seating options are visible immediately near the camera. |
| [612763115119258](https://www.mapillary.com/app/?pKey=612763115119258) | steps | yes | no | There are no visible benches or seating areas immediately near the camera. |
| [612763115119258](https://www.mapillary.com/app/?pKey=612763115119258) | shade | yes | no | There are no visible benches or seating areas immediately near the camera. |
| [649280031492904](https://www.mapillary.com/app/?pKey=649280031492904) | seat | no | yes | There are steps leading up to the main path, but no visible seating area near the camera. |
| [649280031492904](https://www.mapillary.com/app/?pKey=649280031492904) | steps | yes | no | There are steps leading up to the main path, but no visible seating area near the camera. |
| [695926273602514](https://www.mapillary.com/app/?pKey=695926273602514) | steps | yes | no | The immediate area near the camera shows a curb and pavement, but no visible seating. |
| [732217629203237](https://www.mapillary.com/app/?pKey=732217629203237) | steps | yes | no | The immediate area near the camera shows a curb and pavement, but no visible seating. |
| [744774091563369](https://www.mapillary.com/app/?pKey=744774091563369) | shade | yes | no | No visible seating options are present in the immediate foreground area. |
| [874870851696106](https://www.mapillary.com/app/?pKey=874870851696106) | steps | yes | no | There are no visible benches or seating areas immediately near the camera. |
| [879323391866058](https://www.mapillary.com/app/?pKey=879323391866058) | steps | yes | no | The immediate area near the camera shows a curb and tram tracks, with no visible seating. |
| [879323391866058](https://www.mapillary.com/app/?pKey=879323391866058) | shade | yes | no | The immediate area near the camera shows a curb and tram tracks, with no visible seating. |
| [930719073129385](https://www.mapillary.com/app/?pKey=930719073129385) | steps | yes | no | The immediate area near the camera shows a curb and a crosswalk, but no visible seating. |
| [930719073129385](https://www.mapillary.com/app/?pKey=930719073129385) | shade | yes | no | The immediate area near the camera shows a curb and a crosswalk, but no visible seating. |
| [960936106425438](https://www.mapillary.com/app/?pKey=960936106425438) | shade | yes | no | There is a metal bench visible on the paved sidewalk near the street sign. |

### gemma4:e2b

| Photo | Question | Gemma said | Truth | Gemma's note |
|---|---|---|---|---|
| [1000891198977675](https://www.mapillary.com/app/?pKey=1000891198977675) | shade | yes | no | No obvious seating is visible in the immediate foreground area. |
| [1011607371182857](https://www.mapillary.com/app/?pKey=1011607371182857) | shade | yes | no | No obvious seating is visible in the immediate foreground of the street. |
| [1084284310213353](https://www.mapillary.com/app/?pKey=1084284310213353) | shade | yes | no | No obvious seating is visible near the camera in this view. |
| [1287583996406352](https://www.mapillary.com/app/?pKey=1287583996406352) | shade | yes | no | No obvious seating is visible in the immediate foreground. |
| [1320968576170587](https://www.mapillary.com/app/?pKey=1320968576170587) | shade | yes | no | No obvious seating is visible in the immediate foreground area. |
| [1353833989490796](https://www.mapillary.com/app/?pKey=1353833989490796) | shade | yes | no | There are no visible benches or seating areas in the immediate foreground. |
| [1436760738496985](https://www.mapillary.com/app/?pKey=1436760738496985) | shade | yes | no | No obvious seating is visible in the immediate foreground of the photo. |
| [1519398533522093](https://www.mapillary.com/app/?pKey=1519398533522093) | shade | yes | no | No obvious seating is visible in the immediate foreground of the street. |
| [1534806274732060](https://www.mapillary.com/app/?pKey=1534806274732060) | shade | yes | no | No obvious seating is visible near the camera in this street scene. |
| [1621064212647976](https://www.mapillary.com/app/?pKey=1621064212647976) | shade | yes | no | There are shadows cast on the pavement from trees, indicating shade is present. |
| [1710874073259089](https://www.mapillary.com/app/?pKey=1710874073259089) | shade | yes | no | No obvious seating is visible in the immediate foreground area. |
| [1740307813796316](https://www.mapillary.com/app/?pKey=1740307813796316) | shade | yes | no | No obvious seating is visible in the immediate foreground of the street. |
| [1900133340677216](https://www.mapillary.com/app/?pKey=1900133340677216) | shade | yes | no | No obvious seating is visible in the immediate vicinity of the camera. |
| [2025483165029194](https://www.mapillary.com/app/?pKey=2025483165029194) | shade | yes | no | No obvious seating is visible in the immediate vicinity of the camera. |
| [25284584147904790](https://www.mapillary.com/app/?pKey=25284584147904790) | shade | yes | no | No obvious seating is visible in the immediate vicinity of the camera. |
| [612763115119258](https://www.mapillary.com/app/?pKey=612763115119258) | shade | yes | no | There are no visible benches or seating areas immediately near the camera. |
| [649280031492904](https://www.mapillary.com/app/?pKey=649280031492904) | seat | no | yes | There are no visible benches or seating areas near the camera in this view. |
| [649280031492904](https://www.mapillary.com/app/?pKey=649280031492904) | steps | yes | no | There are no visible benches or seating areas near the camera in this view. |
| [695926273602514](https://www.mapillary.com/app/?pKey=695926273602514) | shade | yes | no | No obvious seating is visible near the camera in this street view. |
| [744774091563369](https://www.mapillary.com/app/?pKey=744774091563369) | shade | yes | no | There are no visible benches or seating areas in the immediate foreground. |
| [845965878009140](https://www.mapillary.com/app/?pKey=845965878009140) | shade | yes | no | No obvious seating is visible in the immediate vicinity of the camera. |
| [879323391866058](https://www.mapillary.com/app/?pKey=879323391866058) | shade | yes | no | No obvious seating is visible near the camera in this street scene. |
| [928867469533135](https://www.mapillary.com/app/?pKey=928867469533135) | seat | no | yes | No seating is visible in the immediate foreground area. |
| [928867469533135](https://www.mapillary.com/app/?pKey=928867469533135) | shade | yes | no | No seating is visible in the immediate foreground area. |
| [930719073129385](https://www.mapillary.com/app/?pKey=930719073129385) | shade | yes | no | No obvious seating is visible in the immediate foreground of the street. |
