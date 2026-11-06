# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/helmut-hoffer-von-ankershoffen/heinzel-plugins/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                                  |    Stmts |     Miss |   Branch |   BrPart |   Cover |   Missing |
|------------------------------------------------------ | -------: | -------: | -------: | -------: | ------: | --------: |
| src/heinzel\_plugin\_tools/\_\_init\_\_.py            |        0 |        0 |        0 |        0 |    100% |           |
| src/heinzel\_plugin\_tools/\_\_main\_\_.py            |        2 |        2 |        0 |        0 |      0% |       3-5 |
| src/heinzel\_plugin\_tools/\_historical\_galleries.py |        3 |        0 |        0 |        0 |    100% |           |
| src/heinzel\_plugin\_tools/\_presentation.py          |       87 |       11 |       36 |        6 |     83% |35-36, 44, 50, 61, 71, 79-82, 194 |
| src/heinzel\_plugin\_tools/audit.py                   |       32 |        2 |       10 |        2 |     90% |   12, 103 |
| src/heinzel\_plugin\_tools/capture.py                 |      666 |       57 |      306 |       50 |     89% |32, 69, 71-\>67, 146-\>145, 167, 175, 182, 199, 206, 210, 217, 220, 227, 235, 243, 250, 253, 256, 272, 274, 278, 291, 293-295, 303, 328, 332-333, 378, 385, 419, 423, 426, 450, 529, 559-\>571, 562-565, 583-585, 586-\>exit, 642, 706, 711-712, 713-\>715, 759, 765, 773, 823, 1066, 1067-\>1028, 1129-1130, 1152, 1154-1155, 1165, 1199, 1244-\>1246, 1251 |
| src/heinzel\_plugin\_tools/cli.py                     |      671 |       15 |      310 |       18 |     97% |36, 148-\>145, 340-\>334, 500, 504-\>506, 524, 527, 540, 569, 624, 867, 884, 892, 895-\>899, 1176-\>1183, 1197-1198, 1218, 1220, 1262 |
| src/heinzel\_plugin\_tools/installation.py            |      109 |       10 |       18 |        3 |     90% |56-\>58, 59, 125-\>119, 207-215 |
| src/heinzel\_plugin\_tools/planning.py                |      100 |       12 |       28 |        8 |     84% |69, 106, 113, 130-131, 206-207, 209, 217, 219, 225, 231 |
| src/heinzel\_plugin\_tools/privacy.py                 |      197 |        6 |       92 |        4 |     97% |63, 78, 95, 220-221, 321 |
| src/heinzel\_plugin\_tools/publishing.py              |      220 |        5 |      120 |        4 |     97% |180-\>184, 205, 307-\>311, 319-322 |
| src/heinzel\_plugin\_tools/vendor.py                  |      528 |       18 |      298 |       20 |     95% |178, 190, 197, 201, 204, 247, 251, 286, 299, 320, 360, 365, 515, 518, 544, 571-\>573, 653-\>656, 668, 713, 844 |
| **TOTAL**                                             | **2615** |  **138** | **1218** |  **115** | **93%** |           |


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