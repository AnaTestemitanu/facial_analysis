import boto3
from PIL import Image
import io

def merge_images_from_s3(bucket_name , prefix, grid_size):
    # Create clients for S3 and Rekognition services
    s3 = boto3.client("s3")

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
        # Resize the current image to the calculated cell size
        resized_image = image.resize((cell_width, cell_height), Image.ANTIALIAS)
        # Paste the resized image into the result image at the calculated position
        result.paste(resized_image, (x, y))



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

    return temp_key


