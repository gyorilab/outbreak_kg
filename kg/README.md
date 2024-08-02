# Building the Docker image

docker build --tag captrs:kg .

# Running the Docker container
docker run -it -p 7474:7474 -p 7687:7687 captrs:kg
