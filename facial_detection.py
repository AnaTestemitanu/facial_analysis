"""
The script performs the following steps:

Imports the required libraries: boto3 for accessing Amazon Web Services (AWS), io for reading and writing binary data, 
and PIL for handling images.
Defines a function detect_faces which takes two parameters: bucket_name and prefix.
Connects to the S3 storage service and the Rekognition service on AWS using boto3 clients.
Lists all the S3 objects with the specified prefix in the bucket_name.
Iterates over the S3 objects and retrieves the image data from each object, converting it to a PIL image.
Merges the images into a single image.
Saves the merged image to S3 temporarily.
Calls the detect_faces method of the Rekognition service on the merged image to detect faces and get their attributes.
Stores the face data into a list of dictionaries.
Sorts the face data list based on the grid position of the face in the merged image.
Deletes the temporary merged image from S3.
Returns the face data list.

"""


# facial_detection.py
import boto3
import io
from PIL import Image


def detect_faces(bucket_name, prefix):
    # Create clients for S3 and Rekognition services
    s3 = boto3.client("s3")
    rekognition = boto3.client("rekognition")

    try:
        # Get a list of S3 objects with the specified prefix
        response = s3.list_objects(Bucket=bucket_name, Prefix=prefix)
    except Exception as e:
        # Print error message if an exception occurs while listing objects
        print(f"Error listing objects in S3 bucket: {bucket_name} with prefix: {prefix}. Error: {str(e)}")
        raise e

    # Extract the keys (file names) of the objects from the response
    keys = [content['Key'] for content in response['Contents']]

    images = []
    for key in keys:
        try:
            # Get the object from S3
            object = s3.get_object(Bucket=bucket_name, Key=key)
        except Exception as e:
            # If an error occurs during retrieval, print error message and continue to next key
            print(f"Error getting object from S3: {key}. Error: {str(e)}")
            continue
        byte_array = object['Body'].read()
        try:
            # Open the image
            image = Image.open(io.BytesIO(byte_array))
            # Append the image to the `images` list
            images.append(image)
        except IOError as e:
            # If an error occurs during reading of the image, print error message and continue to next key
            print(f"Error reading image from S3 object: {key}. Error: {str(e)}")

    if len(images) == 0:
        # If no valid images are found, raise an exception
        raise Exception("No valid images found in the S3 objects")

    # Define the grid size
    grid_size = (4,8)

    # Get the number of rows and columns in the grid
    rows = grid_size[0]
    cols = grid_size[1]

    # Calculate the width of each cell in the grid
    cell_width = int(sum(image.width for image in images) / cols)//2
    # Calculate the height of each cell in the grid
    cell_height = int(max(image.height for image in images) / rows)//2
    # Get the aspect ratios of each image
    aspect_ratios = [image.width/image.height for image in images]
    # Get the max aspect ratio of all images
    max_aspect_ratio = max(aspect_ratios)
    # Update the cell height based on the max aspect ratio
    cell_height = int(cell_width / max_aspect_ratio)
    # Create a new image to store the results, with the calculated grid size
    result = Image.new('RGB', (cell_width * cols, cell_height * rows))
    
    # Loop through the images and paste each one into the result image
    for i, image in enumerate(images):
        # Calculate the x and y position of the current image in the result image
        x = int(i % cols) * cell_width
        y = int(i / cols) * cell_height
        # Resize the current image to fit in the grid cell, and paste it into the result image at the calculated position
        result.paste(image.resize((cell_width, cell_height)), (x, y))
        
    # Save the merged image to S3 temporarily
    temp_key = "temp/merged_image.png"
    result_bytes = io.BytesIO()
    try:
        # Save the result image to a binary stream
        result.save(result_bytes, format='PNG', save_all=True)
    except Exception as e:
        print(f"Error saving merged image: {str(e)}")
        raise e

    result_bytes.seek(0)
    try:
        # Upload the binary stream to S3
        s3.put_object(Bucket=bucket_name, Key=temp_key, Body=result_bytes.getvalue(), ContentType='image/png')
    except Exception as e:
        print(f"Error putting merged image to S3: {temp_key}. Error: {str(e)}")
        raise e

    # Call the detect_faces method of the Rekognition client
    try:
        # Detect faces in the merged image stored in S3
        response = rekognition.detect_faces(Image={"S3Object":
         {"Bucket": bucket_name, 
         "Name": temp_key}}, 
         Attributes=["ALL"])
    except Exception as e:
        print(f"Error calling detect_faces on Rekognition: {str(e)}")
        raise e

    # response from Rekognition
    face_data = []
    # Create a set to store grid positions to ensure uniqueness
    grid_positions = set()
    for face in response['FaceDetails']:
        # Get the bounding box coordinates of the face
        bounding_box = face['BoundingBox']
        # Calculate the grid x and y positions based on the bounding box
        grid_x = int(bounding_box['Left'] * cols)
        grid_y = int(bounding_box['Top'] * rows)
        # Calculate the grid position based on the grid x and y
        grid_position = grid_y * cols + grid_x
        # If the grid position is already in the set, increment it to find a unique position
        while grid_position in grid_positions:
            grid_position += 1
        # Add the grid position to the set of grid positions
        grid_positions.add(grid_position)
        # Sort the emotions based on the confidence level
        emotions = sorted(face['Emotions'], key=lambda x: -x['Confidence']) 
        # Get the age range of the face
        age_range = (face['AgeRange']['Low'], face['AgeRange']['High'])
        # Append the face data to the list of face data
        face_data.append({
            'grid_position': grid_position,
            'age_range': age_range,
            #  Get the highest confidence emotion of the face
            'Highest Confidence Emotion': {
                'Confidence': emotions[0]['Confidence'],
                'Type': emotions[0]['Type']
            }
        })
    # Sort the face data based on the grid position
    face_data = sorted(face_data, key=lambda x: x['grid_position'])


    # Delete the temporary merged image
    # try:
    #     s3.delete_object(Bucket=bucket_name, Key=temp_key)
    # except Exception as e:
    #     print(f"Error deleting temporary image from S3: {temp_key}. Error: {str(e)}")
    #     raise e

    # Return the face data
    return face_data


