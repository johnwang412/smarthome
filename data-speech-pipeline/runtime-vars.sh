# Fix PyTorch 2.6+ weights_only=True compatibility issue with pyannote models
# - without this setting, pyannote models fail to load
export TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD=1
