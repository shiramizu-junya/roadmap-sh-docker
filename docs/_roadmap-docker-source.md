# roadmap.sh/docker 単元素材

出典: https://github.com/kamranahmedse/developer-roadmap
取得日: 2026-09-20

> 各トピックの本文は数行と短い。教材化の素材ではなく、
> 「扱う範囲」の定義として使う（_prompt.md §2.2）。

---

## application-architecture@EqYWfBL5l5OOquok_OvOW

# Application Architecture

Application architecture in containerized environments focuses on designing applications to leverage containerization benefits. This includes microservices patterns, service decomposition, inter-service communication, data persistence strategies, and designing for scalability and fault tolerance in distributed systems.

Visit the following resources to learn more:

- [@official@Docker Application Design Patterns](https://docs.docker.com/get-started/docker-concepts/building-images/)
- [@article@Microservices Architecture](https://microservices.io/)
- [@article@Container Design Patterns](https://kubernetes.io/blog/2016/06/container-design-patterns/)
- [@article@Twelve-Factor App Methodology](https://12factor.net/)
- [@video@Microservices vs Monolith Architecture](https://www.youtube.com/watch?v=GBTdnfD6s5Q)
## bare-metal-vs-vms-vs-containers@3hatcMVLDbMuz73uTx-9P

# Bare Metal vs VM vs Containers

Bare metal runs applications directly on hardware with maximum performance but limited flexibility. VMs use hypervisors to run multiple OS instances with strong isolation but higher overhead. Containers share the host OS kernel, providing lightweight isolation with better resource efficiency than VMs while maintaining portability.

Visit the following resources to learn more:

- [@article@History of Virtualization](https://courses.devopsdirective.com/docker-beginner-to-pro/lessons/01-history-and-motivation/03-history-of-virtualization)
- [@article@Bare Metal Machine](https://glossary.cncf.io/bare-metal-machine/)
- [@article@What is a Virtual Machine?](https://azure.microsoft.com/en-au/resources/cloud-computing-dictionary/what-is-a-virtual-machine)
## basics-of-docker@kIqx7Inf50mE9W0juwNBz

# Docker Basics

Docker is a platform that simplifies building, packaging, and deploying applications in lightweight, portable containers. Key components include Dockerfiles (build instructions), Images (snapshots), and Containers (running instances). Essential commands cover pulling images, building from Dockerfiles, running containers with port mapping, and managing both containers and images.

What is a Container?
--------------------

A container is a lightweight, standalone, and executable software package that includes all the dependencies (libraries, binaries, and configuration files) required to run an application. Containers isolate applications from their environment, ensuring they work consistently across different systems.

Docker Components
-----------------

There are three key components in the Docker ecosystem:

*   **Dockerfile**: A text file containing instructions (commands) to build a Docker image.
*   **Docker Image**: A snapshot of a container, created from a Dockerfile. Images are stored in a registry, like Docker Hub, and can be pulled or pushed to the registry.
*   **Docker Container**: A running instance of a Docker image.

Docker Commands
---------------

Below are some essential Docker commands you'll use frequently:

*   `docker pull <image>`: Download an image from a registry, like Docker Hub.
*   `docker build -t <image_name> <path>`: Build an image from a Dockerfile, where `<path>` is the directory containing the Dockerfile.
*   `docker image ls`: List all images available on your local machine.
*   `docker run -d -p <host_port>:<container_port> --name <container_name> <image>`: Run a container from an image, mapping host ports to container ports.
*   `docker container ls`: List all running containers.
*   `docker container stop <container>`: Stop a running container.
*   `docker container rm <container>`: Remove a stopped container.
*   `docker image rm <image>`: Remove an image from your local machine.
## bind-mounts@wZcCW1ojGzUakHCv2AaI1

# Bind Mounts

Bind mounts have limited functionality compared to volumes. When you use a bind mount, a file or directory on the host machine is mounted into a container. The file or directory is referenced by its absolute path on the host machine. By contrast, when you use a volume, a new directory is created within Docker's storage directory on the host machine, and Docker manages that directory's contents.

Visit the following resources to learn more:

- [@official@Docker Bind Mounts](https://docs.docker.com/storage/bind-mounts/)
## building-container-images@5OEfBQaYNOCi999x6QUqW

# Building Container Images

Container images are executable packages that include everything required to run an application: code, runtime, system tools, libraries, and settings. By building custom images, you can deploy applications seamlessly with all their dependencies on any Docker-supported platform. The key component in building a container image is the `Dockerfile`. It is essentially a script containing instructions on how to assemble a Docker image. Each instruction in the Dockerfile creates a new layer in the image, making it easier to track changes and minimize the image size. Here's a simple example of a Dockerfile:

Visit the following resources to learn more:

- [@official@Docker Build Overview](https://docs.docker.com/build/concepts/overview)
- [@official@Docker Image Builder](https://docs.docker.com/reference/cli/docker/buildx/build/)
- [@official@Dockerfile Reference](https://docs.docker.com/engine/reference/builder/)
- [@opensource@Dockerfile Examples](https://github.com/dockersamples)
## cgroups@fRl4EfNwlBiidzn3IV34-

# cgroups

cgroups (control groups) are Linux kernel features that limit and manage system resources like CPU, memory, and I/O for process groups. Docker uses cgroups to enforce resource constraints on containers, ensuring predictable performance and preventing containers from consuming excessive system resources.

Visit the following resources to learn more:

- [@official@Control Groups](https://www.docker.com/resources/what-container/#control-groups)
- [@article@Control Groups - Medium](https://medium.com/@furkan.turkal/how-does-docker-actually-work-the-hard-way-a-technical-deep-diving-c5b8ea2f0422)
- [@video@An introduction to cgroups, runc & containerD](https://www.youtube.com/watch?v=u1LeMndEk70)
## command-line-utilities@YzpB7rgSR4ueQRLa0bRWa

# Command Line Utilities

Docker images can include command line utilities or standalone applications that we can run inside containers.

Visit the following resources to learn more:

- [@official@Docker Images](https://docs.docker.com/engine/reference/commandline/images/)
- [@official@Docker Run](https://docs.docker.com/reference/cli/docker/container/run/)
- [@official@Docker Pull](https://docs.docker.com/engine/reference/commandline/pull/)
## container-registries@3VKPiMfbGBxv9m_SljIQV

# Container Registries

A Container Registry is a centralized storage and distribution system for Docker container images. It allows developers to easily share and deploy applications in the form of these images. Container registries play a crucial role in the deployment of containerized applications, as they provide a fast, reliable, and secure way to distribute container images across various production environments.

Visit the following resources to learn more:

- [@official@Docker Registry](https://docs.docker.com/registry/)
- [@official@Docker Hub](https://hub.docker.com/)
- [@official@Artifact Registry](https://cloud.google.com/artifact-registry)
- [@official@Amazon ECR](https://aws.amazon.com/ecr/)
- [@official@Azure Container Registry](https://azure.microsoft.com/en-in/products/container-registry)
## container-security@78YFahP3Fg-c27reLkuK4

# Container Security

Container security encompasses a broad set of practices and tools aimed at protecting containerized applications from development through deployment and runtime. It involves securing the container image, ensuring that only trusted and non-vulnerable code is used, implementing strong access controls for container environments, and configuring containers to follow the principle of least privilege. Additionally, it includes monitoring for unexpected behavior, protecting communication between containers, and maintaining the host environment’s security. Effective container security integrates seamlessly into DevSecOps workflows to provide continuous visibility and protection across the container lifecycle without disrupting development speed or agility.

Visit the following resources to learn more:

- [@official@Docker Security](https://docs.docker.com/engine/security/)
- [@article@Kubernetes Security Best Practices](https://www.aquasec.com/cloud-native-academy/kubernetes-in-production/kubernetes-security-best-practices-10-steps-to-securing-k8s/)
- [@course@Container Security Labs: Privileged Containers, Daemon Exposure, Image Layers](https://ransomleak.com/catalogue/cloud-security/)
## containers@jhwe-xfVc-C7qy8YuS5dZ

# Containers

Containers are isolated, lightweight environments that run applications using a shared operating system kernel, ensuring consistency and portability across different computing environments. They encapsulate everything needed to run an application, such as code, dependencies, and configurations, making it easy to move and run the containerized application anywhere. Using the Docker CLI, you can create, start, stop, and manage containers with commands like `docker run`, `docker ps` to list running containers, `docker stop` to halt them, and `docker exec` to interact with them in real time. The CLI provides a powerful interface for developers to build, control, and debug containers effortlessly, allowing for streamlined development and operational workflows.

Visit the following resources to learn more:

- [@official@Docker CLI Commands](https://docs.docker.com/engine/reference/commandline/cli/)
- [@article@Docker CLI Commands Cheat Sheet](https://docs.docker.com/get-started/docker_cheatsheet.pdf)
## continuous-integration@oyqw4tr-taZcxt5kREh1g

# Continuous Integration (CI)

Continuous integration is the idea of executing some actions (for example build, test, etc...) automatically as you push code to your version control system.

For containers, there are a number of things we may want to do:

*   Build the container images
*   Execute tests
*   Scan container images for vulnerabilities
*   Tag images with useful metadata
*   Push to a container registry

Visit the following resources to learn more:

- [@article@Continuous Integration - Docker](https://courses.devopsdirective.com/docker-beginner-to-pro/lessons/11-development-workflow/04-continuous-integration-github-actions)
- [@feed@Explore top posts about CI/CD](https://app.daily.dev/tags/cicd?ref=roadmapsh)
## data-persistence@uUPYXmwu27SBPqKZx6U_q

# Data Persistence in Docker

Docker enables you to run containers that are isolated pieces of code, including applications and their dependencies, separated from the host operating system. Containers are ephemeral by default, which means any data stored in the container will be lost once it is terminated. To overcome this problem and retain data across container lifecycle, Docker provides various data persistence methods.

Visit the following resources to learn more:

- [@official@Data Persistence - Docker Documentation](https://docs.docker.com/get-started/docker-concepts/running-containers/persisting-container-data/)
## databases@jKSE_wKYf4P9wnSh_LkMi

# Using Databases

Running your database in a Docker container can help streamline your development process and ease deployment. Docker Hub provides numerous pre-made images for popular databases such as MySQL, PostgreSQL, and MongoDB.

Visit the following resources to learn more:

- [@official@Containerized Databases](https://docs.docker.com/guides/use-case/databases/)
- [@video@How to Setup MySQL Database with Docker](https://www.youtube.com/watch?v=igc2zsOKPJs)
## debuggers@LiAV9crrTHhLqeZhD25a2

# Debuggers in Docker

In order to make developing with containers competitive with developing locally, we need the ability to run and attach to debuggers inside the container.

Visit the following resources to learn more:

- [@official@Docker Buildx Debug](https://docs.docker.com/reference/cli/docker/buildx/debug/)
- [@article@Debuggers in Docker](https://courses.devopsdirective.com/docker-beginner-to-pro/lessons/11-development-workflow/02-debug-and-test)
## deploying-containers@qXOGqORi3EdqwsP9Uhi9m

# Deploying Containers

Deploying containers is a crucial step in using Docker and containerization to manage applications more efficiently, easily scale, and ensure consistent performance across environments. This topic will give you an overview of how to deploy Docker containers to create and run your applications.

Visit the following resources to learn more:

- [@official@Docker Deployment](https://docs.docker.com/guides/orchestration/)
- [@official@Docker Compose](https://docs.docker.com/compose/)
- [@official@Docker Swarm](https://docs.docker.com/engine/swarm/)
## developer-experience@hHXTth0ZP8O-iMGR9xfu9

# Developer Experience

Docker significantly enhances the developer experience by providing a consistent, isolated environment for building, testing, and running applications, eliminating the “it works on my machine” problem. With Docker, developers can package their applications and dependencies into portable containers, ensuring consistency across different environments, from local development to staging and production. The simplified setup and reproducibility of environments accelerate onboarding, minimize conflicts, and allow developers to focus on coding rather than troubleshooting configurations. Moreover, tools like Docker Compose enable quick orchestration of complex multi-container applications, making it easier to prototype, iterate, and collaborate, ultimately streamlining the entire development lifecycle.

Visit the following resources to learn more:

- [@official@Docker Developer Experience](https://www.docker.com/blog/cto-chat-overcoming-the-developer-experience-gap-feat-redmonk-flow-io/)
- [@article@Developer Experience Wishlist - Docker](https://courses.devopsdirective.com/docker-beginner-to-pro/lessons/11-development-workflow/00-devx-wishlist#key-devx-features)
## docker-and-oci@43drPbTwPqJQPyzwYUdBT

# Docker and OCI

The Open Container Initiative (OCI) is a Linux Foundation project which aims at creating industry standards for container formats and runtimes. Its primary goal is to ensure the compatibility and interoperability of container environments through defined technical specifications.

Visit the following resources to learn more:

- [@official@Open Container Initiative](https://opencontainers.org/)
- [@article@OCI - Wikipedia](https://en.wikipedia.org/wiki/Open_Container_Initiative)
## docker-cli@b-LwyYiegbF0jIrn7HYRv

# Docker CLI

The Docker Command Line Interface (CLI) is a powerful tool used to interact with the Docker engine, enabling developers and operators to build, manage, and troubleshoot containers and related resources. With a wide range of commands, the Docker CLI provides control over all aspects of Docker, including creating and managing containers (`docker run`, `docker stop`), building images (`docker build`), managing networks (`docker network`), handling storage (`docker volume`), and inspecting system status (`docker ps`, `docker info`). Its intuitive syntax and flexibility allow users to automate complex workflows, streamline development processes, and maintain containerized applications with ease, making it a foundational utility for Docker management and orchestration.

Visit the following resources to learn more:

- [@official@Docker CLI](https://docs.docker.com/reference/cli/docker/)
- [@official@Docker Compose](https://docs.docker.com/compose/)
## docker-compose@jjA9E0J8N2frfeJCNtA1m

# Docker Compose

Docker Compose is a tool for defining and running multi-container applications using a YAML file (`docker-compose.yml`). It describes application services, networks, and volumes, enabling you to create, manage, and run entire containerized applications with single commands for simplified orchestration.

Visit the following resources to learn more:

- [@official@Docker Compose documentation](https://docs.docker.com/compose/)
- [@opensource@Curated Docker Compose Samples](https://github.com/docker/awesome-compose?tab=readme-ov-file)
- [@video@Docker Compose Tutorial](https://www.youtube.com/watch?v=DM65_JyGxCo)
## docker-desktop-winmaclinux@NCdsPRhJy7UtQFNLo1J1f

# Docker Desktop

Docker Desktop is a comprehensive development environment for Windows, macOS, and Linux with a GUI. It includes Docker Engine, CLI, Buildx, Extensions, Compose, Kubernetes, and credentials helper, providing everything needed for container development on desktop platforms.

Visit the following resources to learn more:

- [@official@Docker Desktop Documentation](https://docs.docker.com/desktop/)
- [@official@Docker Get Started Guide](https://docs.docker.com/get-started/)
- [@official@Docker Hub](https://hub.docker.com/)
- [@feed@Explore top posts about Docker](https://app.daily.dev/tags/docker?ref=roadmapsh)
## docker-engine--linux@0NKqLUWtJMlXn-m6wpA6f

# Docker Engine

Docker Engine is the core open-source containerization runtime that creates and manages containers, builds images, and provides the Docker API. It runs on Linux, Windows, and macOS, serving as the foundation for Docker Desktop and standalone Docker installations on servers.

Visit the following resources to learn more:

- [@official@Docker Engine Installation Guide](https://docs.docker.com/engine/install/)
- [@official@Docker Engine - Docker Documentation](https://docs.docker.com/engine/)
- [@video@Docker Engine for Linux Servers Setup and Tips](https://www.youtube.com/watch?v=YeF7ObTnDwc)
- [@feed@Explore top posts about Docker](https://app.daily.dev/tags/docker?ref=roadmapsh)
## docker-run@6eu5NRA1sJuaHTlHtNurc

# Running Containers

The `docker run` command creates and starts a new container from a specified image. It combines `docker create` and `docker start` operations, offering a range of options to customize the container's runtime environment. Users can set environment variables, map ports and volumes, define network connections, and specify resource limits. The command supports detached mode for background execution, interactive mode for shell access, and the ability to override the default command defined in the image. Common flags include `-d` for detached mode, `-p` for port mapping, `-v` for volume mounting, and `--name` for assigning a custom container name. Understanding `docker run` is fundamental to effectively deploying and managing Docker containers.

Visit the following resources to learn more:

- [@official@Docker Run](https://docs.docker.com/engine/reference/commandline/run/)
## docker-swarm@ks6PFN-0Z9zH7gtWaWgxz

# Docker Swarm

Docker Swarm is Docker’s native container orchestration tool that allows users to deploy, manage, and scale containers across a cluster of Docker hosts. By transforming a group of Docker nodes into a single, unified cluster, Swarm provides high availability, load balancing, and automated container scheduling using simple declarative commands. With features like service discovery, rolling updates, and integrated security through TLS encryption, Docker Swarm offers an approachable alternative to more complex orchestrators like Kubernetes. Its tight integration with the Docker CLI and ease of setup make it a suitable choice for small to medium-sized deployments where simplicity and straightforward management are priorities.

Visit the following resources to learn more:

- [@official@Docker Swarm](https://docs.docker.com/engine/swarm/)
## dockerfiles@yGRQcx64S-yBGEoOeMc55

# Dockerfile

A Dockerfile is a text document that contains a list of instructions used by the Docker engine to build an image. Each instruction in the Dockerfile adds a new layer to the image. Docker will build the image based on these instructions, and then you can run containers from the image.

Visit the following resources to learn more:

- [@official@Dockerfile Reference](https://docs.docker.com/engine/reference/builder/)
- [@official@Dockerfile Best Practices](https://docs.docker.com/develop/develop-images/dockerfile_best-practices/)
- [@opensource@Dockerfile Examples](https://github.com/dockersamples)
## dockerhub@rxVR62_yXIjc-L4GFSV6u

# DockerHub

Docker Hub is a cloud-based registry service that serves as the primary public repository for Docker container images. It allows users to store, share, and distribute Docker images, offering both free public repositories and paid private ones and integrates seamlessly with Docker CLI, enabling easy pushing and pulling of images. It features official images maintained by software vendors, automated builds linked to source code repositories, and webhooks for triggering actions based on repository events.

Visit the following resources to learn more:

- [@official@DockerHub](https://hub.docker.com/)
- [@official@DockerHub Repositories](https://docs.docker.com/docker-hub/repos/)
- [@official@DockerHub Webhooks](https://docs.docker.com/docker-hub/webhooks/)
## efficient-layer-caching@frshJqVMP8D7o_7tMZMPI

# Efficient Layer Caching

When building container images, Docker caches the newly created layers. These layers can then be used later on when building other images, reducing the build time and minimizing bandwidth usage. However, to make the most of this caching mechanism, you should be aware of how to efficiently use layer caching. Docker creates a new layer for each instruction (e.g., `RUN`, `COPY`, `ADD`, etc.) in the Dockerfile. If the instruction hasn't changed since the last build, Docker will reuse the existing layer.

Visit the following resources to learn more:

- [@official@Docker Layer Caching](https://docs.docker.com/build/cache/)
- [@video@Layer Caching](https://www.youtube.com/watch?v=_nMpndIyaBU)
## ephemeral-container-filesystem@086zZYjtzdCaDHm-MkSqg

# Ephemeral FS

By default, the storage within a Docker container is ephemeral, meaning that any data changes or modifications made inside a container will only persist until the container is stopped and removed. Once the container is stopped and removed, all the associated data will be lost. This is because Docker containers are designed to be stateless by nature. This temporary or short-lived storage is called the "ephemeral container file system". It is an essential feature of Docker, as it enables fast and consistent deployment of applications across different environments without worrying about the state of a container.

Visit the following resources to learn more:

- [@official@Data Persistence - Docker Documentation](https://docs.docker.com/get-started/docker-concepts/running-containers/persisting-container-data/)
- [@video@Docker Concepts - Persisting container data](https://www.youtube.com/watch?v=10_2BjqB_Ls)
## hot-reloading@4p5d3rzCHy4vjg2PRX-2k

# Hot Reloading in Docker

Even though we can speed up the image building with layer caching enable, we don't want to have to rebuild our container image with every code change. Instead, we want the state of our application in the container to reflect changes immediately. We can achieve this through a combination of bind mounts and hot reloading utilities!

Visit the following resources to learn more:

- [@article@Hot Reloading - Docker](https://courses.devopsdirective.com/docker-beginner-to-pro/lessons/11-development-workflow/01-hot-reloading)
## image-security@M5UG-ZcyhBPbksZd0ZdNt

# Image Security

Image security is a crucial aspect of deploying Docker containers in your environment. Ensuring the images you use are secure, up to date, and free of vulnerabilities is essential. In this section, we will review best practices and tools for securing and managing your Docker images. When pulling images from public repositories, always use trusted, official images as a starting point for your containerized applications. Official images are vetted by Docker and are regularly updated with security fixes. You can find these images on the Docker Hub or other trusted registries.

Visit the following resources to learn more:

- [@official@Docker Content Trust](https://docs.docker.com/engine/security/trust/content_trust/)
- [@official@Docker Hub](https://hub.docker.com/)
- [@course@Secrets in Image Layers: Hands-on Exercise](https://ransomleak.com/exercises/secrets-in-image-layers/)
## image-size-and-security@-8wAzF6_3gruiM3VYMvB0

# Reducing Image Size

Reducing Docker image size is crucial for optimizing storage, transfer speeds, and deployment times. Key strategies include using minimal base images like Alpine Linux, leveraging multi-stage builds to exclude unnecessary build tools, removing unnecessary files and packages, and minimizing the number of layers by combining commands.

Visit the following resources to learn more:

- [@official@Multi-stage builds](https://docs.docker.com/build/building/multi-stage/)
- [@official@Docker Best Practices](https://docs.docker.com/develop/develop-images/dockerfile_best-practices/)
- [@feed@Explore top posts about Security](https://app.daily.dev/tags/security?ref=roadmapsh)
## image-tagging-best-practices@Vs4WQwgJFhA63U9Gf2ym0

# Image Tagging Best Practices

Docker image tagging best practices center on creating clear, consistent, and informative labels. Adopt semantic versioning for releases, avoid the ambiguous "latest" tag in production, and include relevant metadata like build dates or Git commit hashes. Implement a strategy distinguishing between environments, use descriptive tags for variants, and automate tagging in CI/CD pipelines. Regularly clean up old tags and document your conventions to maintain clarity and facilitate team-wide adoption. These practices ensure efficient image management and improve collaboration across your organization.

Visit the following resources to learn more:

- [@official@Docker Tags](https://docs.docker.com/get-started/docker-concepts/building-images/build-tag-and-publish-an-image/)
- [@article@Docker Image Tagging Best Practices](https://medium.com/@nirmalkushwah08/docker-image-tagging-strategy-4aa886fb4fcc)
- [@article@Semantic Versioning](https://semver.org/)
## images@3Nsg-F3wMKEzEsXw1MBZv

# Docker Images

Docker images are lightweight, standalone packages containing everything needed to run software: application code, runtime, libraries, and system tools. Built in layers for efficient storage, they serve as blueprints for containers and can be shared through registries like Docker Hub for consistent deployment across environments.

Visit the following resources to learn more:

- [@article@What's the Difference Between Docker Images and Containers?](https://aws.amazon.com/compare/the-difference-between-docker-images-and-containers/)
- [@video@What is an image?](https://www.youtube.com/watch?v=NyvT9REqLe4)
## installation--setup@01nDXqxVdMv4SeXc0nYHH

# Installation Setup

Docker provides Docker Desktop, a desktop application that simplifies installation and setup with GUI capabilities. Alternatively, you can install Docker Engine for command-line only functionality without graphical interface components.

Visit the following resources to learn more:

- [@official@Docker Desktop website](https://www.docker.com/products/docker-desktop)
- [@official@Docker Engine](https://docs.docker.com/engine/install/)
## introduction@Py9nst2FDJ1_hoXeX_qSF

# What is Docker?

Docker is an open-source platform that automates application deployment, scaling, and management using lightweight, portable containers. Containers are standalone executable units containing all necessary dependencies, libraries, and configuration files for consistent application execution across various environments.

Visit the following resources to learn more:

- [@official@Docker](https://www.docker.com/)
- [@official@Docker Docs](https://docs.docker.com/)
## kubernetes@RqXpX2XabtHYVjgg1EZR_

# Kubernetes

Kubernetes is an open-source container orchestration platform designed to automate the deployment, scaling, and management of containerized applications. It provides a robust framework for handling complex container workloads by organizing containers into logical units called pods, managing service discovery, load balancing, and scaling through declarative configurations. Kubernetes enables teams to deploy containers across clusters of machines, ensuring high availability and fault tolerance through self-healing capabilities like automatic restarts, replacements, and rollback mechanisms. With its extensive ecosystem and flexibility, Kubernetes has become the de facto standard for running large-scale, distributed applications, simplifying operations and improving the reliability of containerized workloads.

Visit the following resources to learn more:

- [@official@Kubernetes](https://kubernetes.io/)
- [@official@Docker Swarm](https://docs.docker.com/engine/swarm/)
## namespaces@BvV8VCX39wRB-g8WvGF1g

# What are Namespaces?

Docker namespaces are a Linux kernel feature that creates isolated environments for containers by providing separate instances of global system resources. Docker uses PID, NET, MNT, UTS, IPC, and USER namespaces to ensure each container believes it has its own unique resources, enabling lightweight, portable, and secure containerization.

Visit the following resources to learn more:

- [@official@Docker Namespaces](https://docs.docker.com/engine/security/userns-remap/)
- [@article@Linux Namespaces](https://man7.org/linux/man-pages/man7/namespaces.7.html)
## networks@w5QjzvOaciK2rotOkjvjQ

# Docker Networks

Docker networks enable containers to communicate with each other and with external systems, providing the necessary connectivity for microservices architectures. By default, Docker offers several network types such as bridge, host, and overlay, each suited for different use cases like isolated environments, high-performance scenarios, or multi-host communication. Using the Docker CLI, you can create, inspect, and manage networks with commands like `docker network create` to define custom networks, `docker network ls` to list existing networks, and `docker network connect` to attach a container to a network. This flexibility allows developers to control how containers interact, ensuring secure and efficient communication across distributed applications.

Visit the following resources to learn more:

- [@official@Docker Networks](https://docs.docker.com/network/)
- [@official@Docker Network Commands](https://docs.docker.com/engine/reference/commandline/network/)
- [@video@Docker Networking](https://www.youtube.com/watch?v=bKFMS5C4CG0)
## nomad@r1eJZDZYouUjnGwAtRbyU

# Nomad: Deploying Containers

Nomad is a cluster manager and scheduler that enables you to deploy, manage and scale your containerized applications. It automatically handles node failures, resource allocation, and container orchestration. Nomad supports running Docker containers as well as other container runtime(s) and non-containerized applications.

Visit the following resources to learn more:

- [@official@Nomad Documentation](https://www.nomadproject.io/docs)
## others-ghcr-ecr-gcr-acr-etc@fh5aERX7c-lY9FPsmftoF

# DockerHub Alternatives

Container images can be stored in many different registries, not just Dockerhub. Most major cloud platforms now provide container registries such as "Artifact Registry" on Google Cloud Platform, Elastic Container Registry on AWS and Azure Container Registry on Microsoft Azure. GitHub also provides it's own registry which is useful when container builds are included in your GitHub Actions workflow.

Visit the following resources to learn more:

- [@official@DockerHub](https://hub.docker.com/)
- [@official@Artifact Registry](https://cloud.google.com/artifact-registry)
- [@official@Amazon ECR](https://aws.amazon.com/ecr/)
- [@official@Azure Container Registry](https://azure.microsoft.com/en-in/products/container-registry)
- [@official@GitHub Container Registry](https://docs.github.com/en/packages/guides/about-github-container-registry)
## paas-options@PP_RRBo_pThe2mgf6xzMP

# PaaS Options for Deploying Containers

Platform-as-a-Service (PaaS) options for deploying containers provide a simplified and managed environment where developers can build, deploy, and scale containerized applications without worrying about the underlying infrastructure. Popular PaaS offerings include Google Cloud Run, Azure App Service, AWS Elastic Beanstalk, and Heroku, which abstract away container orchestration complexities while offering automated scaling, easy integration with CI/CD pipelines, and monitoring capabilities. These platforms support rapid development and deployment by allowing teams to focus on application logic rather than server management, providing a seamless way to run containers in production with minimal operational overhead.

Visit the following resources to learn more:

- [@official@PaaS Options for Deploying Containers](https://www.docker.com/resources/what-container/#paas-options)
- [@official@Azure Container Instances](https://azure.microsoft.com/en-us/services/container-instances/)
- [@official@Google Cloud Run](https://cloud.google.com/run)
- [@official@IBM Cloud Code Engine](https://www.ibm.com/cloud/code-engine)
- [@official@Amazon Elastic Container Service](https://aws.amazon.com/ecs/)
## package-managers@mw-weCutd2ECKlx2DE_ZJ

# Package Managers

Package managers are tools used to install, update, and manage software packages on Linux systems. Since most Docker images are based on Linux distributions, understanding package managers like `apt` (Debian/Ubuntu), `yum`/`dnf` (RHEL/CentOS/Fedora), and `apk` (Alpine Linux) is essential for building Docker images. In a Dockerfile, you typically use `RUN` instructions with package managers to install the dependencies your application needs, and it is a best practice to clean up package caches afterward to keep image sizes small.

Visit the following resources to learn more:

- [@article@APT Package Manager Guide](https://ubuntu.com/server/docs/package-management)
- [@article@Alpine Linux Package Management](https://wiki.alpinelinux.org/wiki/Alpine_Package_Keeper)
- [@video@Linux Package Managers Explained](https://www.youtube.com/watch?v=-iSMFoPPbKU)
- [@feed@Explore top posts about Docker](https://app.daily.dev/tags/docker?ref=roadmapsh)

## programming-languages@XxT9UUjbKW1ARyERSLH_W

# Programming Languages

Having proficiency in at least one programming language is essential before working with Docker, as containers are ultimately used to package and run applications. Whether you work with Python, JavaScript, Go, Java, or any other language, understanding how your application is built, its dependencies, and its runtime requirements directly informs how you write Dockerfiles and structure container images. Knowledge of your language's package management, build tools, and runtime environment helps you create efficient, minimal Docker images tailored to your application's needs.

Visit the following resources to learn more:

- [@roadmap@Python Roadmap](https://roadmap.sh/python)
- [@roadmap@JavaScript Roadmap](https://roadmap.sh/javascript)
- [@roadmap@Java Roadmap](https://roadmap.sh/java)
- [@roadmap@Go Roadmap](https://roadmap.sh/golang)
- [@feed@Explore top posts about Docker](https://app.daily.dev/tags/docker?ref=roadmapsh)

## running-containers@z2eeBXPzo-diQ67Fcfyhc

# Running Containers

The `docker run` command creates and starts containers from images in one step. It combines `docker create` and `docker start` operations, allowing you to execute applications in isolated environments with various configuration options like port mapping, volumes, and environment variables.

Visit the following resources to learn more:

- [@official@Docker Run](https://docs.docker.com/engine/reference/commandline/run/)
- [@official@Docker Containers](https://docs.docker.com/engine/reference/commandline/container/)
- [@official@Docker Exec](https://docs.docker.com/engine/reference/commandline/exec/)
- [@official@Docker Stop](https://docs.docker.com/engine/reference/commandline/stop/)
## runtime-configuration-options@mAaEz-bwB5DLaBbOSYGMn

# Runtime Configuration Options

Docker runtime configuration options give you powerful control over your containers' environments. By tweaking resource limits, network settings, security profiles, and logging drivers, you can optimize performance and enhance security. You'll also find options for setting environment variables, mounting volumes, and overriding default behaviors – all crucial for tailoring containers to your specific needs. For more advanced users, there are tools to adjust kernel capabilities and set restart policies. Whether you're using command-line flags or Docker Compose files, these options help ensure your containers run smoothly and consistently, no matter where they're deployed.

Visit the following resources to learn more:

- [@official@Docker Documentation](https://docs.docker.com/engine/reference/run/)
- [@article@Docker Runtime Arguments](https://galea.medium.com/docker-runtime-arguments-604593479f45)
## runtime-security@vYug8kcwrMoWf8ft4UDNI

# Runtime Security

Runtime security in Docker focuses on ensuring the safety and integrity of containers during their execution, safeguarding against vulnerabilities and malicious activities that could arise while the containerized application is running. This involves monitoring container behavior for anomalies, implementing access controls to limit permissions, and employing tools to detect and respond to suspicious activity in real time. Effective runtime security also ensures that only verified images are deployed and continuously audits the system to maintain compliance, thereby providing a robust defense layer to prevent exploits and maintain the desired security posture throughout the container lifecycle.

Visit the following resources to learn more:

- [@official@Docker Security](https://docs.docker.com/engine/security/)
- [@official@Docker Security Best Practices](https://docs.docker.com/build/building/best-practices/)
- [@course@Privileged Containers: Hands-on Escape Exercise](https://ransomleak.com/exercises/privileged-containers/)
## shell-commands@W5kX5jn49hghRgkEw6_S3

# Shell Commands

Shell commands are the fundamental way to interact with Linux-based systems that Docker containers typically run on. Understanding commands like `ls`, `cd`, `cp`, `mv`, `rm`, `chmod`, `chown`, `ps`, `top`, `grep`, `find`, and `cat` is essential for working inside containers, writing Dockerfiles, and debugging running containers. When you use `docker exec` to access a running container or write `RUN` instructions in a Dockerfile, you rely on these shell commands to install dependencies, configure environments, and manage files within the container's filesystem.

Visit the following resources to learn more:

- [@article@Linux Command Line Basics](https://www.freecodecamp.org/news/the-linux-commands-handbook/)
- [@article@Shell Commands Every Developer Should Know](https://www.codecademy.com/article/command-line-commands)
- [@video@Linux Commands for Beginners](https://www.youtube.com/watch?v=ZtqBQ68cfJc)
- [@feed@Explore top posts about Docker](https://app.daily.dev/tags/docker?ref=roadmapsh)

## shell-scripting@InlMtuaUJ9EXO-OD9x1jj

# Shell Scripting

Shell scripting involves writing scripts using shell languages like Bash to automate tasks and workflows. In the context of Docker, shell scripts are commonly used in Dockerfiles as part of `RUN` instructions to set up the container environment, install packages, or configure applications. They are also used as entrypoint or startup scripts (via `ENTRYPOINT` or `CMD`) to initialize services when a container starts. Understanding variables, conditionals, loops, and functions in shell scripting helps you write more efficient Dockerfiles and manage complex container setups.

Visit the following resources to learn more:

- [@article@Shell Scripting Tutorial](https://www.shellscript.sh/)
- [@article@Bash Scripting Tutorial for Beginners](https://linuxconfig.org/bash-scripting-tutorial-for-beginners)
- [@video@Bash Scripting Full Course](https://www.youtube.com/watch?v=tK9Oc6AEnR4)
- [@feed@Explore top posts about Docker](https://app.daily.dev/tags/docker?ref=roadmapsh)

## tests@Kmyo1_Mor9WHLkRhNShRZ

# Tests

We want to run tests in an environment as similar as possible to production, so it only makes sense to do so inside of our containers! This can include unit tests, integration tests, and end-to-end tests, all run within Docker containers to simulate real-world scenarios while avoiding interference from external dependencies. Using Docker CLI and tools like Docker Compose, you can create isolated testing environments, run tests in parallel, and spin up and tear down the necessary infrastructure automatically.

Visit the following resources to learn more:

- [@article@Running Tests - Docker](https://courses.devopsdirective.com/docker-beginner-to-pro/lessons/11-development-workflow/03-tests)
- [@feed@Explore top posts about Testing](https://app.daily.dev/tags/testing?ref=roadmapsh)
## underlying-technologies@jrH1qE6EnFXL4fTyYU8gR

# Underlying Technologies

Docker containers use Linux kernel technologies for isolation and resource management: namespaces for process isolation, cgroups for resource limits, and union filesystems for efficient layered storage. These enable lightweight, portable, and secure containers that share the host kernel.

Visit the following resources to learn more:

- [@official@Underlying Technologies](https://www.docker.com/resources/what-container/#underlying-technologies)
- [@article@Underlying Technologies - Medium](https://medium.com/@furkan.turkal/how-does-docker-actually-work-the-hard-way-a-technical-deep-diving-c5b8ea2f0422)
- [@video@Containers - Namespaces, Cgroups and Overlay Filesystem](https://www.youtube.com/watch?v=wJdDWc6zO4U)
## union-filesystems@vEUfw_vobshuZI0-q8RZo

# Union Filesystems

Union filesystems (UnionFS) create virtual, layered file structures by overlaying multiple directories without modifying originals. Docker uses this to manage storage efficiently by minimizing duplication and reducing image sizes through layered filesystem approach that keeps directory contents separate while mounted together.

Visit the following resources to learn more:

- [@article@AUFS (Advanced Multi-Layered Unification Filesystem)](http://aufs.sourceforge.net/)
- [@article@OverlayFS (Overlay Filesystem)](https://www.kernel.org/doc/html/latest/filesystems/overlayfs.html)
- [@article@Btrfs (B-Tree Filesystem)](https://btrfs.readthedocs.io/en/stable/)
- [@article@ZFS (Z File System)](https://zfsonlinux.org/)
## users--groups-permissions@uKjB2qntFTpPuYUT9sdxd

# Users / Groups Permissions

Linux users, groups, and file permissions control access to files and resources on the system. In Docker, understanding these concepts is important because containers run processes as specific users, and the permissions model determines what files a containerized application can read, write, or execute. By default, containers run as root, which poses security risks, so it is a best practice to create non-root users in your Dockerfile using `RUN useradd` and switch to them with the `USER` instruction. Commands like `chmod`, `chown`, and `chgrp` help you set the correct permissions on files and directories within your container images.

Visit the following resources to learn more:

- [@article@Linux File Permissions Explained](https://www.redhat.com/en/blog/linux-file-permissions-explained)
- [@article@Users and Groups in Linux](https://wiki.archlinux.org/title/Users_and_groups)
- [@official@Dockerfile USER Instruction](https://docs.docker.com/reference/dockerfile/#user)
- [@feed@Explore top posts about Docker](https://app.daily.dev/tags/docker?ref=roadmapsh)

## using-3rd-party-container-images@LShK3-1EGGuXnEvdScFR7

# Using Third Party Images

Third-party images are pre-built Docker container images that are available on Docker Hub or other container registries. These images are created and maintained by individuals or organizations and can be used as a starting point for your containerized applications.

Visit the following resources to learn more:

- [@official@Docker Hub Registry](https://hub.docker.com/)
- [@course@Malicious Base Images: Hands-on Exercise](https://ransomleak.com/exercises/malicious-base-images/)
## volume-mounts@woemCQmWTR-hIoWAci3d5

# Volume Mounts

Volume mounts are a way to map a folder or file on the host system to a folder or file inside a container. This allows the data to persist outside the container even when the container is removed. Additionally, multiple containers can share the same volume, making data sharing between containers easy.

Visit the following resources to learn more:

- [@official@Docker Volumes](https://docs.docker.com/storage/volumes/)
- [@official@Docker Volume Flags](https://docs.docker.com/storage/bind-mounts/#choose-the--v-or---mount-flag)
- [@video@Docker Volumes explained in 6 minutes](https://www.youtube.com/watch?v=p2PH_YPCsis)
## volumes@eHtVLB6v3h7hatJb-9cZK

# Docker Volumes

Docker volumes are persistent storage solutions used to manage and store data outside the container's filesystem, ensuring data remains intact even if the container is deleted or recreated. They are ideal for storing application data, logs, and configuration files that need to persist across container restarts and updates. With the Docker CLI, you can create and manage volumes using commands like `docker volume create` to define a new volume, `docker volume ls` to list all volumes, and `docker run -v` to mount a volume to a specific container. This approach helps maintain data integrity, simplifies backup processes, and supports data sharing between containers, making volumes a core part of stateful containerized applications.

Visit the following resources to learn more:

- [@official@Docker Volumes](https://docs.docker.com/storage/volumes/)
- [@official@Docker Volume Commands](https://docs.docker.com/engine/reference/commandline/volume/)
## what-are-containers@74JxgfJ_1qmVNZ_QRp9Ne

# What are Containers?

Containers are lightweight, portable, and isolated software environments that package applications with their dependencies for consistent execution across different platforms. They streamline development, deployment, and management while ensuring applications run reliably regardless of underlying infrastructure.

Visit the following resources to learn more:

- [@course@Introduction to Containers - AWS Skill Builder](https://explore.skillbuilder.aws/learn/course/106/introduction-to-containers)
- [@official@What is a Container?](https://www.docker.com/resources/what-container/)
- [@feed@Explore top posts about Containers](https://app.daily.dev/tags/containers?ref=roadmapsh)
## why-do-we-need-containers@i4ijY3T5gLgNz0XqRipXe

# Need for Containers

Containers solve environment inconsistency issues when working in teams by standardizing runtime environments. Before containers, significant time was lost configuring local environments to run projects shared by teammates, leading to "works on my machine" problems.

Visit the following resources to learn more:

- [@article@Need for Containers](https://www.redhat.com/en/topics/containers)