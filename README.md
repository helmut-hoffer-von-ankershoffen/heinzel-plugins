# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/helmut-hoffer-von-ankershoffen/heinzel-plugins/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                                  |    Stmts |     Miss |   Branch |   BrPart |   Cover |   Missing |
|------------------------------------------------------ | -------: | -------: | -------: | -------: | ------: | --------: |
| src/heinzel\_plugin\_tools/\_\_init\_\_.py            |        0 |        0 |        0 |        0 |    100% |           |
| src/heinzel\_plugin\_tools/\_\_main\_\_.py            |        2 |        2 |        0 |        0 |      0% |       3-5 |
| src/heinzel\_plugin\_tools/\_historical\_galleries.py |        3 |        0 |        0 |        0 |    100% |           |
| src/heinzel\_plugin\_tools/audit.py                   |       32 |        2 |       10 |        2 |     90% |   12, 103 |
| src/heinzel\_plugin\_tools/capture.py                 |      661 |       57 |      304 |       51 |     88% |32, 68, 70-\>66, 145-\>144, 166, 174, 181, 198, 205, 209, 216, 219, 226, 234, 242, 249, 252, 255, 271, 273, 277, 290, 292-294, 302, 327, 331-332, 377, 384, 418, 422, 425, 449, 528, 558-\>570, 561-564, 582-584, 585-\>exit, 641, 696, 701-702, 703-\>705, 749, 755, 763, 813, 907-\>909, 1054, 1055-\>1016, 1115-1116, 1138, 1140-1141, 1151, 1185, 1230-\>1232, 1237 |
| src/heinzel\_plugin\_tools/cli.py                     |      671 |       15 |      310 |       18 |     97% |36, 148-\>145, 340-\>334, 500, 504-\>506, 524, 527, 540, 569, 624, 867, 884, 892, 895-\>899, 1176-\>1183, 1197-1198, 1218, 1220, 1262 |
| src/heinzel\_plugin\_tools/installation.py            |       96 |       10 |       12 |        2 |     89% |56-\>58, 59, 190-198 |
| src/heinzel\_plugin\_tools/planning.py                |      100 |       12 |       28 |        8 |     84% |69, 106, 113, 130-131, 202-203, 205, 213, 215, 221, 227 |
| src/heinzel\_plugin\_tools/privacy.py                 |      197 |        6 |       92 |        4 |     97% |63, 78, 95, 220-221, 321 |
| src/heinzel\_plugin\_tools/publishing.py              |      220 |        5 |      120 |        4 |     97% |180-\>184, 205, 307-\>311, 319-322 |
| src/heinzel\_plugin\_tools/vendor.py                  |      463 |       13 |      266 |       20 |     95% |66, 70, 105, 118, 126-\>130, 139, 140-\>135, 164-\>163, 179, 184, 329, 332, 358, 361-\>356, 385-\>387, 396-\>389, 467-\>470, 482, 527, 653 |
| **TOTAL**                                             | **2445** |  **122** | **1142** |  **109** | **93%** |           |


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