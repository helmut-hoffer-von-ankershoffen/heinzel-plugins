# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/helmut-hoffer-von-ankershoffen/heinzel-plugins/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                                  |    Stmts |     Miss |   Branch |   BrPart |   Cover |   Missing |
|------------------------------------------------------ | -------: | -------: | -------: | -------: | ------: | --------: |
| src/heinzel\_plugin\_tools/\_\_init\_\_.py            |        0 |        0 |        0 |        0 |    100% |           |
| src/heinzel\_plugin\_tools/\_\_main\_\_.py            |        2 |        2 |        0 |        0 |      0% |       3-5 |
| src/heinzel\_plugin\_tools/\_digest\_migration.py     |        1 |        0 |        0 |        0 |    100% |           |
| src/heinzel\_plugin\_tools/\_historical\_galleries.py |        3 |        0 |        0 |        0 |    100% |           |
| src/heinzel\_plugin\_tools/\_presentation.py          |       87 |       11 |       36 |        6 |     83% |35-36, 44, 50, 61, 71, 79-82, 194 |
| src/heinzel\_plugin\_tools/audit.py                   |       53 |        2 |       20 |        2 |     95% |   12, 144 |
| src/heinzel\_plugin\_tools/capture.py                 |      733 |       58 |      330 |       51 |     89% |37, 76, 78-\>74, 153-\>152, 174, 182, 189, 206, 213, 217, 224, 227, 234, 242, 250, 257, 260, 263, 279, 281, 285, 298, 300-302, 310, 335, 339-340, 377, 440, 447, 513, 517, 520, 544, 623, 653-\>665, 656-659, 677-679, 680-\>exit, 736, 800, 805-806, 807-\>809, 853, 859, 867, 917, 1198, 1199-\>1160, 1261-1262, 1284, 1286-1287, 1297, 1331, 1376-\>1378, 1383 |
| src/heinzel\_plugin\_tools/cli.py                     |      756 |       16 |      348 |       20 |     97% |36, 148-\>145, 349, 438-\>432, 556-\>exit, 613, 617-\>619, 637, 640, 653, 682, 737, 980, 997, 1005, 1008-\>1012, 1349-\>1356, 1370-1371, 1391, 1393, 1435 |
| src/heinzel\_plugin\_tools/focused\_policy.py         |       79 |        9 |       32 |        7 |     84% |187, 190, 203-204, 210, 212, 226, 233-234 |
| src/heinzel\_plugin\_tools/installation.py            |      109 |       10 |       18 |        3 |     90% |56-\>58, 59, 125-\>119, 207-215 |
| src/heinzel\_plugin\_tools/planning.py                |      103 |       12 |       28 |        8 |     85% |76, 113, 120, 137-138, 213-214, 216, 224, 226, 232, 238 |
| src/heinzel\_plugin\_tools/privacy.py                 |      197 |        6 |       92 |        4 |     97% |63, 78, 95, 220-221, 321 |
| src/heinzel\_plugin\_tools/publishing.py              |      265 |        9 |      138 |        5 |     96% |69-71, 194, 247-\>251, 272, 376-\>380, 397-400 |
| src/heinzel\_plugin\_tools/vendor.py                  |      539 |       19 |      304 |       21 |     95% |178, 190, 197, 201, 204, 247, 251, 286, 299, 320, 360, 365, 515, 518, 539, 558, 585-\>587, 667-\>670, 682, 727, 858 |
| **TOTAL**                                             | **2927** |  **154** | **1346** |  **127** | **93%** |           |


## Setup coverage badge

Below are examples of the badges you can use in your main branch `README` file.

### Direct image

[![Coverage badge](https://raw.githubusercontent.com/helmut-hoffer-von-ankershoffen/heinzel-plugins/python-coverage-comment-action-data/badge.svg)](https://htmlpreview.github.io/?https://github.com/helmut-hoffer-von-ankershoffen/heinzel-plugins/blob/python-coverage-comment-action-data/htmlcov/index.html)

This is the one to use if your repository is private or if you don't want to customize anything.

### [Shields.io](https://shields.io) Json Endpoint

[![Coverage badge](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/helmut-hoffer-von-ankershoffen/heinzel-plugins/python-coverage-comment-action-data/endpoint.json)](https://htmlpreview.github.io/?https://github.com/helmut-hoffer-von-ankershoffen/heinzel-plugins/blob/python-coverage-comment-action-data/htmlcov/index.html)

Using this one will allow you to [customize](https://shields.io/endpoint) the look of your badge.
It won't work with private repositories. It won't be refreshed more than once per five minutes.

### [Shields.io](https://shields.io) Dynamic Badge

[![Coverage badge](https://img.shields.io/badge/dynamic/json?color=brightgreen&label=coverage&query=%24.message&url=https%3A%2F%2Fraw.githubusercontent.com%2Fhelmut-hoffer-von-ankershoffen%2Fheinzel-plugins%2Fpython-coverage-comment-action-data%2Fendpoint.json)](https://htmlpreview.github.io/?https://github.com/helmut-hoffer-von-ankershoffen/heinzel-plugins/blob/python-coverage-comment-action-data/htmlcov/index.html)

This one will always be the same color. It won't work for private repos. I'm not even sure why we included it.

## What is that?

This branch is part of the
[python-coverage-comment-action](https://github.com/marketplace/actions/python-coverage-comment)
GitHub Action. All the files in this branch are automatically generated and may be
overwritten at any moment.