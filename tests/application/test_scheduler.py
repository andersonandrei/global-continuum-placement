from typing import List

import pytest

from global_continuum_placement.domain.placement.placement import Placement
from global_continuum_placement.domain.platform.platform import Platform
from global_continuum_placement.domain.scheduling_policies.exceptions import (
    NotEnoughResourcesException,
)
from global_continuum_placement.domain.workload.workload import (
    Flow,
    UnknownArchitectureError,
)


async def test_scheduler_schedule_without_constraints(
    application_dict, scheduler_service_mock
):
    application = Flow.create_from_dict(application_dict)
    placements: List[Placement] = await scheduler_service_mock.schedule_flow(
        application
    )
    assert len(placements) == len(application_dict["functions"])


@pytest.mark.parametrize(
    "application_dict",
    [
        pytest.param(
            {"id": "task1", "annotations": {"cores": 2000}},
            id="not enough CPU resources",
        ),
        pytest.param(
            {"id": "task1", "annotations": {"cores": 1, "memory": 100e6}},
            id="not enough Memory resources",
        ),
    ],
)
async def test_scheduler_schedule_not_enough_resources(
    scheduler_service_mock,
    application_dict,
):
    application = Flow.create_from_dict({"functions": [application_dict]})
    with pytest.raises(NotEnoughResourcesException):
        await scheduler_service_mock.schedule_flow(application)


@pytest.mark.parametrize(
    "application_dict,expected_placements",
    [
        pytest.param(
            {
                "id": "task1",
                "resources": {"nb_cpu": 1},
                "allocations": ["site1"],
            },
            [Placement("site1", "task1")],
            id="cluster constraints",
        ),
        pytest.param(
            {
                "id": "task1",
                "resources": {"nb_cpu": 1},
                "annotations": {"locality": "HPC"},
            },
            [Placement("site3", "task1")],
            id="cluster type constraints",
        ),
    ],
)
async def test_scheduler_schedule_site_constraints(
    scheduler_service_mock, application_dict, expected_placements
):
    application = Flow.create_from_dict({"functions": [application_dict]})
    placements: List[Placement] = await scheduler_service_mock.schedule_flow(
        application
    )
    assert placements == expected_placements


def test_scheduler_architecture_invalid_constraint():
    workflow_dict = {
        "functions": [
            {
                "id": "task1",
                "resources": {"nb_cpu": 1},
                "annotations": {"architecture": "NOTEXITS"},
            }
        ]
    }
    with pytest.raises(UnknownArchitectureError):
        Flow.create_from_dict(workflow_dict)


@pytest.mark.parametrize(
    "application_dict,expected_placements",
    [
        pytest.param(
            {
                "id": "taskARM",
                "resources": {"nb_cpu": 1},
                "annotations": {"architecture": "arm64"},
            },
            [Placement("site2", "taskARM")],
            id="arm64 constraint",
        ),
        pytest.param(
            {
                "id": "taskX86",
                "resources": {"nb_cpu": 1},
                "annotations": {"architecture": "x86_64"},
            },
            [Placement("site1", "taskX86")],
            id="x86_64 constraint",
        ),
    ],
)
async def test_scheduler_architecture_constraints(
    scheduler_service_mock, application_dict, expected_placements
):
    application = Flow.create_from_dict({"functions": [application_dict]})
    placements: List[Placement] = await scheduler_service_mock.schedule_flow(
        application
    )
    assert placements == expected_placements


@pytest.mark.parametrize(
    "platform_dict,application_dict,expected_placements",
    [
        pytest.param(
            {
                "site1": {
                    "type": "Edge",
                    "resources": {"nb_cpu": 1},
                    "objective_scores": {
                        "Energy": 1,
                        "Availability": 5,
                        "Performance": 25,
                    },
                },
                "site2": {
                    "type": "Edge",
                    "resources": {"nb_cpu": 1},
                    "objective_scores": {
                        "Energy": 100,
                        "Availability": 30,
                        "Performance": 50,
                    },
                },
            },
            {
                "functions": [{"id": "task1", "annotations": {"cores": 1}}],
                "objectives": {"Energy": "High"},
            },
            [Placement("site2", "task1")],
            id="mono objective",
        ),
        pytest.param(
            {
                "site1": {
                    "type": "Edge",
                    "resources": {"nb_cpu": 1},
                    "objective_scores": {
                        "Energy": 100,
                        "Availability": 5,
                        "Performance": 25,
                    },
                },
                "site2": {
                    "type": "Edge",
                    "resources": {"nb_cpu": 1},
                    "objective_scores": {
                        "Energy": 100,
                        "Availability": 30,
                        "Performance": 50,
                    },
                },
            },
            {
                "functions": [{"id": "task1", "annotations": {"cores": 1}}],
                "objectives": {"Energy": "Medium"},
            },
            [Placement("site1", "task1")],
            id="mono objective equals",
        ),
        pytest.param(
            {
                "site1": {
                    "type": "Edge",
                    "resources": {"nb_cpu": 1},
                    "objective_scores": {
                        "Energy": 100,
                        "Availability": 30,
                        "Performance": 25,
                    },
                },
                "site2": {
                    "type": "Edge",
                    "resources": {"nb_cpu": 1},
                    "objective_scores": {
                        "Energy": 100,
                        "Availability": 100,
                        "Performance": 50,
                    },
                },
            },
            {
                "functions": [{"id": "task1", "annotations": {"cores": 1}}],
                "objectives": {"Energy": "High", "Availability": "High"},
            },
            [Placement("site2", "task1")],
            id="two objectives same level",
        ),
        pytest.param(
            {
                "site1": {
                    "type": "Edge",
                    "resources": {"nb_cpu": 1},
                    "objective_scores": {
                        "Energy": 100,
                        "Availability": 30,
                        "Performance": 25,
                    },
                },
                "site2": {
                    "type": "Edge",
                    "resources": {"nb_cpu": 1},
                    "objective_scores": {
                        "Energy": 100,
                        "Availability": 100,
                        "Performance": 50,
                    },
                },
            },
            {
                "functions": [{"id": "task1", "annotations": {"cores": 1}}],
                "objectives": {"Energy": "High", "Availability": "Low"},
            },
            [Placement("site2", "task1")],
            id="two objectives different level",
        ),
        pytest.param(
            {
                "site1": {
                    "type": "Edge",
                    "resources": {"nb_cpu": 1},
                    "objective_scores": {
                        "Energy": 100,
                        "Availability": 30,
                        "Performance": 25,
                    },
                },
                "site2": {
                    "type": "Edge",
                    "resources": {"nb_cpu": 1},
                    "objective_scores": {
                        "Energy": 100,
                        "Availability": 100,
                        "Performance": 50,
                    },
                },
                "site3": {
                    "type": "Edge",
                    "resources": {"nb_cpu": 1},
                    "objective_scores": {
                        "Energy": 100,
                        "Availability": 10,
                        "Performance": 90,
                    },
                },
            },
            {
                "functions": [{"id": "task1", "annotations": {"cores": 1}}],
                "objectives": {
                    "Energy": "High",
                    "Availability": "Low",
                    "Performance": "Medium",
                },
            },
            [Placement("site3", "task1")],
            id="three objectives different level",
        ),
        pytest.param(
            {
                "site1": {
                    "type": "Edge",
                    "resources": {"nb_cpu": 1},
                    "objective_scores": {
                        "Energy": 100,
                        "Availability": 30,
                        "Performance": 25,
                    },
                },
                "site2": {
                    "type": "Edge",
                    "resources": {"nb_cpu": 1},
                    "objective_scores": {
                        "Energy": 100,
                        "Availability": 100,
                        "Performance": 50,
                    },
                },
                "site3": {
                    "type": "Edge",
                    "resources": {"nb_cpu": 1, "nb_gpu": 0, "memory_in_MB": 1024},
                    "objective_scores": {
                        "Energy": 100,
                        "Availability": 10,
                        "Performance": 90,
                    },
                },
            },
            {
                "executorMode": "Service",
                "flowID": "1234",
                "annotations": {"memory": 256},
                "functions": [{"id": "task1", "annotations": {"cores": 1}}],
                "objectives": {
                    "Energy": "High",
                    "Availability": "Low",
                    "Performance": "Medium",
                },
            },
            [Placement("site3", "1234")],
            id="three objectives different level",
        ),
    ],
)
async def test_objective_scoring(
    scheduler_service_mock, platform_dict, application_dict, expected_placements
):
    application = Flow.create_from_dict(application_dict)
    platform = Platform.create_from_dict(platform_dict)
    scheduler_service_mock.platform_service.get_platform.return_values = platform
    placements: List[Placement] = await scheduler_service_mock.schedule_flow(
        application
    )
    assert placements == expected_placements
