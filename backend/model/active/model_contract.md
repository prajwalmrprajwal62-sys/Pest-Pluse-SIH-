# PestPulse Model Contract

Model version: v1.0.0
Artifact format: TensorFlow SavedModel
Signature: serving_default
Input key: image
Output key: output_0
Input shape: [1, 224, 224, 3]
Input dtype: float32
Classes: ["Tomato___Bacterial_spot", "Tomato___Early_blight", "Tomato___Septoria_leaf_spot", "Tomato___Target_Spot"]
Preprocessing: embedded MobileNetV2 preprocessing; RGB 224x224 input
Review threshold: 0.8
Unknown threshold: 0.55
Field validation: not performed

This artifact produces a screening signal for human review. It is not a definitive diagnosis, pesticide prescription, outbreak confirmation, or Maharashtra field-accuracy guarantee.

The backend must validate model_manifest.json, labels.json, preprocessing.json, output dimension, and artifact hash before serving predictions.
