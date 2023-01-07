from pathlib import Path
from typing import Any

import pytest

from fairseq2.cli import DynamicModule

MY_SCRIPT = """
def f1(x: int, y: int = 2) -> int:
    return x + y

def f2(x: int, z: int = 2) -> int:
    return x + z

def z(x: int) -> int:
    return x * x

def ret_x(x: int = 1) -> int:
    return x

def loop1(loop2: int) -> int:
    return 3 * loop2

def loop2(loop1: int) -> int:
    return loop1 - 1

def obj():
    return object()

def obj_id(obj) -> int:
    return id(obj)
"""


@pytest.fixture(scope="session")
def script_path(tmp_path_factory: Any) -> Path:
    cli_dir: Path = tmp_path_factory.mktemp("cli")
    script_path = cli_dir / "script.py"
    script_path.write_text(MY_SCRIPT)
    return script_path


def test_call_fn_only_optional(script_path: Path) -> None:
    module = DynamicModule.from_script(script_path)
    assert module.call_fn("ret_x", caller="test") == 1


def test_call_fn_overrides_default(script_path: Path) -> None:
    module = DynamicModule.from_script(script_path, overrides=["x=3", "y=5"])
    assert module.call_fn("ret_x", caller="test") == 3
    assert module.call_fn("f1", caller="test") == 3 + 5


def test_call_fn_multi_step(script_path: Path) -> None:
    module = DynamicModule.from_script(script_path, overrides=["x=3"])
    assert module.call_fn("ret_x", caller="test") == 3
    assert module.call_fn("z", caller="test") == 9
    assert module.call_fn("f2", caller="test") == 3 + 9
    assert module.call_fn("f1", caller="test") == 3 + 2


def test_call_fn_detects_loop(script_path: Path) -> None:
    module = DynamicModule.from_script(script_path)
    with pytest.raises(Exception, match="loop detected: loop1 -> loop2 -> loop1"):
        module.call_fn("loop1", caller="test")


def test_call_fn_overrides_fn(script_path: Path) -> None:
    module = DynamicModule.from_script(script_path, overrides=["f1=0", "loop1=5"])
    assert module.call_fn("f1", caller="test") == 0
    assert module.call_fn("loop1", caller="test") == 5


def test_call_fn_missing_arg(script_path: Path) -> None:
    module = DynamicModule.from_script(script_path)
    with pytest.raises(Exception, match=r"Can't call f1, missing args: \['x'\]"):
        module.call_fn("f1", caller="test")


def test_serialize_save_fn_calls(script_path: Path, tmp_path: Path) -> None:
    module = DynamicModule.from_script(script_path, overrides=["x=5"])
    f1 = module.call_fn("f1", caller="test")
    workdir_script = module.serialize(tmp_path, script_path)

    module2 = DynamicModule.from_script(workdir_script)
    assert module2.call_fn("f1", caller="test") == f1


def test_serialize_skip_objects(script_path: Path, tmp_path: Path) -> None:
    module = DynamicModule.from_script(script_path)
    obj_id = module.call_fn("obj_id", caller="test")
    workdir_script = module.serialize(tmp_path, script_path)
    assert list(module._cache.keys()) == ["obj", "obj_id"]

    module2 = DynamicModule.from_script(workdir_script)
    # We saved obj_id, but not obj since there is no trivial serialization for it.
    assert list(module2._cache.keys()) == ["obj_id"]
    assert module2.call_fn("obj_id", caller="test") == obj_id