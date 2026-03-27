__all__ = ["InferenceCore", "MatAnyone2"]


def __getattr__(name):
    if name == "InferenceCore":
        from matanyone2.inference.inference_core import InferenceCore
        return InferenceCore
    if name == "MatAnyone2":
        from matanyone2.model.matanyone2 import MatAnyone2
        return MatAnyone2
    raise AttributeError(name)
