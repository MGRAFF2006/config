export ALICEVISION_ROOT=/usr
export MESHROOM_NODES_PATH=$ALICEVISION_ROOT/share/meshroom:$MESHROOM_NODES_PATH
export MESHROOM_PIPELINE_TEMPLATES_PATH=$ALICEVISION_ROOT/share/meshroom:$MESHROOM_PIPELINE_TEMPLATES_PATH
export ALICEVISION_SENSOR_DB=/usr/share/aliceVision/cameraSensors.db
# Tree is installed by the meshroom package; set path so ImageMatching works without GUI env hacks.
export ALICEVISION_VOCTREE=/usr/share/aliceVision/vlfeat_K80L3.SIFT.tree
