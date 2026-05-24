
import joblib
import numpy as np
import pickle

from google.cloud.aiplatform.prediction.predictor import Predictor
from google.cloud.aiplatform.utils import prediction_utils

from sklearn.datasets import load_iris


class CprPredictor(Predictor):

    def __init__(self):
        return

    def load(self, artifacts_uri: str):
        """Loads the preprocessor and model artifacts."""
        prediction_utils.download_model_artifacts(artifacts_uri)

        with open("preprocessor.pkl", "rb") as f:
            preprocessor = pickle.load(f)

        self._class_names = load_iris().target_names
        self._model = joblib.load("model.joblib")
        self._preprocessor = preprocessor

    def predict(self, instances):
        """Performs prediction."""
        instances = instances["instances"]
        inputs = np.asarray(instances)
        preprocessed_inputs = self._preprocessor.preprocess(inputs)
        outputs = self._model.predict(preprocessed_inputs)

        return {"predictions": [self._class_names[class_num] for class_num in outputs]}
