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
| src/heinzel\_plugin\_tools/capture.py                 |      733 |       57 |      330 |       50 |     90% |37, 77, 79-\>75, 154-\>153, 175, 183, 190, 207, 214, 218, 225, 228, 235, 243, 251, 258, 261, 264, 280, 282, 286, 299, 301-303, 311, 336, 340-341, 378, 441, 448, 514, 518, 521, 545, 624, 654-\>666, 657-660, 678-680, 681-\>exit, 737, 806-807, 808-\>810, 854, 860, 868, 918, 1199, 1200-\>1161, 1262-1263, 1285, 1287-1288, 1298, 1332, 1377-\>1379, 1384 |
| src/heinzel\_plugin\_tools/cli.py                     |      821 |       18 |      370 |       22 |     97% |38, 150-\>147, 390, 489-\>483, 615-\>exit, 672, 678-\>680, 687, 690, 703, 732, 787, 1030, 1047, 1055, 1058-\>1062, 1213, 1215, 1438-\>1445, 1459-1460, 1480, 1482, 1524 |
| src/heinzel\_plugin\_tools/focused\_policy.py         |       79 |        9 |       32 |        7 |     84% |187, 190, 203-204, 210, 212, 226, 233-234 |
| src/heinzel\_plugin\_tools/installation.py            |      111 |        1 |       18 |        3 |     97% |56-\>58, 59, 125-\>119 |
| src/heinzel\_plugin\_tools/planning.py                |      103 |       12 |       28 |        8 |     85% |76, 113, 120, 137-138, 213-214, 216, 224, 226, 232, 238 |
| src/heinzel\_plugin\_tools/privacy.py                 |      198 |        6 |       92 |        4 |     97% |67, 82, 99, 224-225, 325 |
| src/heinzel\_plugin\_tools/publishing.py              |      305 |       14 |      160 |        7 |     94% |72-74, 130, 226, 279-\>283, 304, 425-\>429, 433-436, 451-454 |
| src/heinzel\_plugin\_tools/vendor.py                  |      539 |       19 |      304 |       21 |     95% |178, 190, 197, 201, 204, 247, 251, 286, 299, 320, 360, 365, 515, 518, 539, 558, 585-\>587, 667-\>670, 682, 727, 858 |
| **TOTAL**                                             | **3035** |  **151** | **1390** |  **130** | **93%** |           |


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