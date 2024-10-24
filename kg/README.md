# Building the Docker image

```bash
docker build --tag captrs:kg .
```

# Running the Docker container
```bash
docker run -it -p 7474:7474 -p 7687:7687 -p 8771:8771 captrs:kg
```
