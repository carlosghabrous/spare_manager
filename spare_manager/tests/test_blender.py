import pytest

import spare_manager.config_blender as blender

def run_security_checks_throws_assertionerror_if_different_classes(op, spare):
    with pytest.raises(AssertionError):
        blender.run_security_checks(op, spare)

def run_security_checks_throws_assertionerror_if_different_gateways(op, spare):
    with pytest.raises(AssertionError):
        blender.run_security_checks(op, spare)

def create_mixed_config_returns_spare_config_if_op_empty(op, spare):
    pass

def create_mixed_config_returns_op_config_if_spare_empty(op, spare):
    pass
