# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/helmut-hoffer-von-ankershoffen/heinzel-plugins/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                       |    Stmts |     Miss |   Branch |   BrPart |   Cover |   Missing |
|------------------------------------------- | -------: | -------: | -------: | -------: | ------: | --------: |
| src/heinzel\_plugin\_tools/\_\_init\_\_.py |        0 |        0 |        0 |        0 |    100% |           |
| src/heinzel\_plugin\_tools/\_\_main\_\_.py |        2 |        2 |        0 |        0 |      0% |       3-5 |
| src/heinzel\_plugin\_tools/audit.py        |       21 |        1 |        4 |        1 |     92% |        84 |
| src/heinzel\_plugin\_tools/capture.py      |      650 |      304 |      298 |       53 |     52% |32, 65, 67-\>63, 142-\>141, 163, 171, 178, 195, 202, 206, 208-\>210, 213, 216, 223, 231, 239, 246, 249, 252, 268, 270, 274, 276, 287, 289-291, 299, 324, 326-329, 351-\>353, 353-\>355, 355-\>357, 374, 381, 414, 418, 421, 432, 441, 507-518, 523-562, 567-575, 620, 627, 630, 635, 674-679, 685, 690-691, 692-\>694, 738, 744, 751, 761-\>764, 786-\>789, 801, 809-819, 825, 855, 862-1153, 1158-1201, 1205 |
| src/heinzel\_plugin\_tools/cli.py          |      655 |       13 |      306 |       16 |     97% |141-\>138, 333-\>327, 483, 487-\>489, 507, 510, 522, 601, 840, 857, 865, 868-\>872, 1149-\>1156, 1170-1171, 1191, 1193, 1235 |
| src/heinzel\_plugin\_tools/installation.py |       96 |       10 |       12 |        2 |     89% |56-\>58, 59, 190-198 |
| src/heinzel\_plugin\_tools/planning.py     |       97 |       12 |       28 |        8 |     84% |64, 100, 107, 124-125, 185-186, 188, 196, 198, 204, 210 |
| src/heinzel\_plugin\_tools/privacy.py      |      157 |        4 |       80 |        2 |     97% |58, 73, 176-177 |
| src/heinzel\_plugin\_tools/publishing.py   |      220 |        5 |      120 |        4 |     97% |180-\>184, 205, 307-\>311, 319-322 |
| **TOTAL**                                  | **1898** |  **351** |  **848** |   **86** | **81%** |           |


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