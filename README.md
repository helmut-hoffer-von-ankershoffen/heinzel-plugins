# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/helmut-hoffer-von-ankershoffen/heinzel-plugins/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                                  |    Stmts |     Miss |   Branch |   BrPart |   Cover |   Missing |
|------------------------------------------------------ | -------: | -------: | -------: | -------: | ------: | --------: |
| src/heinzel\_plugin\_tools/\_\_init\_\_.py            |        0 |        0 |        0 |        0 |    100% |           |
| src/heinzel\_plugin\_tools/\_\_main\_\_.py            |        2 |        2 |        0 |        0 |      0% |       3-5 |
| src/heinzel\_plugin\_tools/\_historical\_galleries.py |        3 |        0 |        0 |        0 |    100% |           |
| src/heinzel\_plugin\_tools/\_presentation.py          |       87 |       11 |       36 |        6 |     83% |35-36, 44, 50, 61, 71, 79-82, 194 |
| src/heinzel\_plugin\_tools/audit.py                   |       32 |        2 |       10 |        2 |     90% |   12, 103 |
| src/heinzel\_plugin\_tools/capture.py                 |      690 |       57 |      316 |       50 |     89% |34, 71, 73-\>69, 148-\>147, 169, 177, 184, 201, 208, 212, 219, 222, 229, 237, 245, 252, 255, 258, 274, 276, 280, 293, 295-297, 305, 330, 334-335, 380, 387, 421, 425, 428, 452, 531, 561-\>573, 564-567, 585-587, 588-\>exit, 644, 708, 713-714, 715-\>717, 761, 767, 775, 825, 1106, 1107-\>1068, 1169-1170, 1192, 1194-1195, 1205, 1239, 1284-\>1286, 1291 |
| src/heinzel\_plugin\_tools/cli.py                     |      713 |       15 |      332 |       19 |     97% |36, 148-\>145, 340-\>334, 458-\>exit, 514, 518-\>520, 538, 541, 554, 583, 638, 881, 898, 906, 909-\>913, 1250-\>1257, 1271-1272, 1292, 1294, 1336 |
| src/heinzel\_plugin\_tools/focused\_policy.py         |       79 |        9 |       32 |        7 |     84% |187, 190, 203-204, 210, 212, 226, 233-234 |
| src/heinzel\_plugin\_tools/installation.py            |      109 |       10 |       18 |        3 |     90% |56-\>58, 59, 125-\>119, 207-215 |
| src/heinzel\_plugin\_tools/planning.py                |      100 |       12 |       28 |        8 |     84% |69, 106, 113, 130-131, 206-207, 209, 217, 219, 225, 231 |
| src/heinzel\_plugin\_tools/privacy.py                 |      197 |        6 |       92 |        4 |     97% |63, 78, 95, 220-221, 321 |
| src/heinzel\_plugin\_tools/publishing.py              |      265 |        9 |      138 |        5 |     96% |69-71, 194, 247-\>251, 272, 376-\>380, 397-400 |
| src/heinzel\_plugin\_tools/vendor.py                  |      528 |       18 |      298 |       20 |     95% |178, 190, 197, 201, 204, 247, 251, 286, 299, 320, 360, 365, 515, 518, 544, 571-\>573, 653-\>656, 668, 713, 844 |
| **TOTAL**                                             | **2805** |  **151** | **1300** |  **124** | **93%** |           |


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