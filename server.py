import uvicorn
from fastapi import FastAPI

# Create a FastAPI application
app = FastAPI()


# Define a route for the root URL
@app.get("/")
def hello_world():
    return "Hello, World!"


# Run the application if this script is executed directly
if __name__ == "__main__":
    print("Starting FastAPI server on http://localhost:8000")
    # Run the server with uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
