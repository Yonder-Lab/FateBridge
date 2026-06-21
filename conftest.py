"""pytest 根配置。

它的存在让 pytest 把仓库根目录加入 ``sys.path``，从而 ``tests.*``（如
``tests.golden.canonical``、``tests.fixtures.surface_payloads``）在裸 ``pytest``
调用下也能被导入——CI 用的正是裸 ``pytest``，而非 ``python -m pytest``。
"""
