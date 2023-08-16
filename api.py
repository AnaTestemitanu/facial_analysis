"""
Imports the necessary modules, including Flask, jsonify, and request from the Flask library 
and a custom function detect_faces from a module named facial_detection.

Instantiates a Flask application with app = Flask(__name__).

Defines a route, /detect_faces, that can handle POST requests using the @app.route decorator 
and the detect_faces_api function.

The detect_faces_api function starts by checking if the content type of the request is JSON using request.content_type. 
If it is not, it returns a JSON response with an error message and a 400 status code.

The function then checks if the request contains the necessary parameters, bucket_name and prefix, 
and returns a JSON response with an error message and a 400 status code if they are missing.

The function then retrieves the bucket_name and prefix parameters from the request and passes them 
as arguments to the detect_faces function.

The detect_faces function is called within a try-except block to catch any exceptions. If an exception is raised, 
the function returns a JSON response with the error message and a 500 status code.

If the detect_faces function executes without raising an exception, the function returns its response in JSON format.

The if __name__ == '__main__': block is a standard Python idiom used to check if the script is being run as the main 
program or being imported as a module into another script. If it's being run as the main program, the Flask application 
is run in debug mode.

"""

# api.py
from flask import Flask, jsonify, request
import boto3
import io
import numpy as np
from PIL import Image
from facial_detection import detect_faces
import mergeGrid

# Create a Flask app instance
app = Flask(__name__)


@app.route("/merge-images", methods=["POST"])
def merge_images():
    # Get the JSON data from the request body
    data = request.get_json()
    bucket_name = data.get("bucket_name")
    prefix = data.get("prefix")
    grid_size = data.get("grid_size")

    # Call the merge_images_from_s3 function from the mergeGrid module
    result = mergeGrid.merge_images_from_s3(bucket_name, prefix, grid_size)

    return "Success - 32 images merged!"


# Define a route for the endpoint "/detect_faces" with HTTP POST method
@app.route("/detect_faces", methods=["POST"])
def detect_faces_api():
    # Check if the content type of the request is "application/json"
    if request.content_type != "application/json":
        # Return an error message with HTTP status code 400 (Bad Request) if the content type is invalid
        return jsonify({"error": "Invalid content type, expected application/json"}), 400

    # Check if the required parameters "bucket_name" and "prefix" are present in the request data
    if "bucket_name" not in request.json or "prefix" not in request.json:
        # Return an error message with HTTP status code 400 (Bad Request) if the required parameters are missing
        return jsonify({"error": "Missing required parameters: bucket_name, prefix"}), 400

    # Extract the values of "bucket_name" and "prefix" from the request data    
    bucket_name = request.json['bucket_name']
    prefix = request.json['prefix']


    # Try to run the facial detection function and catch any exceptions
    try:
        response = detect_faces(bucket_name, prefix)
    except Exception as e:
        # Return an error message with HTTP status code 500 (Internal Server Error) if an exception occurs
        return jsonify({"error": str(e)}), 500

    # Return the response from the facial detection function as a JSON object
    return jsonify(response)


import moderation_detection

@app.route("/moderation", methods=["POST"])
def moderation_detection_api():
    bucket = request.args.get("bucket")
    img_path = request.args.get("img_path")
    bucket = request.json['bucket']
    img_path = request.json['img_path']
    
    results = moderation_detection.moderation(bucket, img_path)
    
    return jsonify(results)

  



from detect_custom import show_custom_labels, display_image

@app.route('/detect_custom_labels', methods=['POST'])
def detect_custom_labels():
    bucket = request.json['bucket']
    photo = request.json['photo']
    min_confidence = request.json.get('min_confidence', 7) # Default value set to 50
    model_version = request.json['model']
    response = show_custom_labels(bucket, photo, min_confidence, model_version)

    result_array = display_image(bucket, photo, response)

    return {'grid_positions_and_labels': result_array}



if __name__ == '__main__':
    app.run(debug=True)


