# cloud-complete

`cloud-complete` is a unified testing suite for testing applications for cloud compliance. It was used for testing serverside applications built by the students of PES University (2016-2020) as a part of their Cloud Computing course. It includes four phases of testing:

* REST API Testing - Testing of REST APIs implemented in the application to validate the right kind of responses given various kind of requests.
* Containerization Testing - Testing of the split up of a monolithic service into microservices inside containers with the help of Docker.
* Load Balancer Testing - Testing of path based routing to the two services mentioned above under a single IP or domain.
* Orchestration Testing - Testing of spinning containers up or down based on the frequency of requests a service is receiving (scalability), or bringing a service back up when it forcefully crashes (high availability).
