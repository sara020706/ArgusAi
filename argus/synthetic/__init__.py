"""Synthetic data generation for Argus training and testing."""

from argus.synthetic.generator import (
    events_to_feature_matrix,
    generate_anomalous_event,
    generate_dataset,
    generate_normal_event,
)

__all__ = [
    "generate_normal_event",
    "generate_anomalous_event",
    "generate_dataset",
    "events_to_feature_matrix",
]
