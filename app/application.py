from flask import Flask, request, jsonify,render_template  
import numpy as np
import pandas as pd

# from sklearn.preprocessing import StandardScaler
# from app.components.model_trainer import ModelTrainer

from app.pipeline.predict_pipeline import PredictPipeline, PredictPipeline, customData
application=Flask(__name__, template_folder='../templates')
app=application
#  Routhe for home page
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/predict', methods=['POST','GET'])
def predict_datapoint():
    if request.method == 'POST':
        data=customData(
            gender=request.form['gender'],
            race_ethnicity=request.form['race_ethnicity'],
            parental_level_of_education=request.form['parental_level_of_education'],
            lunch=request.form['lunch'],
            test_preparation_course=request.form['test_preparation_course'],
            reading_score=int(request.form['reading_score']),
            writing_score=int(request.form['writing_score'])
        )
        input_df = data.get_data_as_dataframe()
        print("Input DataFrame:")
        print(input_df)
        # Get the input data from the form
        prediction_pipeline = PredictPipeline()
        prediction = prediction_pipeline.predict(input_df)
        print("Prediction:")
        print(prediction[0])

        return render_template('home.html', prediction=prediction[0])

    return render_template('home.html')


if __name__=="__main__":
    app.run(host="0.0.0.0", port=5000)