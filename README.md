# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/helmut-hoffer-von-ankershoffen/heinzel-plugins/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                       |    Stmts |     Miss |   Branch |   BrPart |   Cover |   Missing |
|------------------------------------------- | -------: | -------: | -------: | -------: | ------: | --------: |
| src/heinzel\_plugin\_tools/\_\_init\_\_.py |        0 |        0 |        0 |        0 |    100% |           |
| src/heinzel\_plugin\_tools/\_\_main\_\_.py |        2 |        2 |        0 |        0 |      0% |       3-5 |
| src/heinzel\_plugin\_tools/audit.py        |       21 |       21 |        4 |        0 |      0% |      3-84 |
| src/heinzel\_plugin\_tools/cli.py          |      573 |      164 |      274 |       54 |     66% |64, 68, 135-142, 147-161, 168, 202, 207-240, 244-256, 260-263, 271, 273, 282-\>284, 332-\>326, 363, 380-389, 409-\>411, 411-\>416, 420, 424, 430-435, 446, 465, 469-\>471, 489, 492, 504, 517-518, 544, 548, 552, 568, 572, 583, 606-\>610, 637, 646, 654, 674, 678-\>680, 696-701, 708, 711, 731-\>733, 733-\>735, 750-752, 763, 780, 788, 791-\>795, 801, 810-812, 816, 821, 825, 839, 849, 851, 936-939, 941-949, 952-\>959, 965, 973-1022, 1032-1034, 1038 |
| src/heinzel\_plugin\_tools/installation.py |       96 |       10 |       12 |        2 |     89% |56-\>58, 59, 190-198 |
| src/heinzel\_plugin\_tools/publishing.py   |      220 |       60 |      120 |       28 |     69% |24-34, 44-\>48, 55, 94, 131, 133, 135, 137, 142, 167, 180-\>184, 183, 185, 195, 202, 205, 208, 210, 214, 221, 223-\>225, 226, 229, 234, 238, 240, 247, 255, 293-315, 319-322 |
| **TOTAL**                                  |  **912** |  **257** |  **410** |   **84** | **67%** |           |


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