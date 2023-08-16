---
title: "Redis cluster to cluster migration"
date: 2023-08-16
categories: ["tech"]
---
>Writing something after a very long time, putting this out as I could not find proper documentation for this task.

Redis<sup>[[1]](https://redis.io/)</sup> has become a de-facto standard for caching and all the use cases of in-memory stores so we chose Redis for caching purposes. Our team offers Platform as a Service (PaaS) which offers Redis to a few of the customers, and we run our components on Kubernetes (K8s).

We chose the K8s operator<sup>[[2]](https://www.redhat.com/en/topics/containers/what-is-a-kubernetes-operator)</sup> way to deploy and manage Redis clusters but we faced issues with the chosen operator so had to move away from it to deploy a stable Redis cluster that can reconcile with changes on K8s cluster like K8s upgrades and restarts. 

Since we had existing customers using the Redis cluster deployed by the operator so it required us to migrate data to the new Redis cluster to make things seamless for end users. We explored a few OSS tools along with Redis's Migrate<sup>[[3]](https://redis.io/commands/migrate/)</sup> command but one that worked for us was RedisShake<sup>[[4]](https://github.com/tair-opensource/RedisShake)</sup>. RedisShake syncs data between the cluster which **includes new writes** on the source cluster which allows us to do a seamless cutover between Redis cluster for applications.

In a cluster setup, data is spread across the masters based on the hash range, every master is isolated with the data it holds so we need to migrate data from every master. By default, RedisShake moves data from one master node only so we need to run RedisShake for every master in the cluster.

Below are the steps to migrate data between Redis clusters using RedisShake -

0. Prerequisite - `python3`, `pip3`
1. Download RedisShake
```bash
mkdir redis-shake
cd redis-shake/
wget https://github.com/tair-opensource/RedisShake/releases/download/v3.1.11/redis-shake-linux-amd64.tar.gz
tar -xvzf redis-shake-linux-amd64.tar.gz
```

2. Get details of the source and target clusters - version, redis master node, username (if using ACL), password, and check if they are `tls` enabled

3. Create `sync.toml` with the above details extracted, sample [reference](https://github.com/tair-opensource/RedisShake/blob/v3/sync.toml)
```toml
type = "sync"

[source]
version = 7.0 # redis version, such as 2.8, 4.0, 5.0, 6.0, 6.2, 7.0, ...
address = "<redis-master-node>:<redis-port>"
username = "" # keep empty if not using ACL
password = "<password>" # keep empty if no authentication is required
tls = true
elasticache_psync = "" # using when source is ElastiCache. ref: https://github.com/alibaba/RedisShake/issues/373

[target]
type = "cluster" # "standalone" or "cluster"
version = 7.0 # redis version, such as 2.8, 4.0, 5.0, 6.0, 6.2, 7.0, ...
# When the target is a cluster, write the address of one of the nodes.
# redis-shake will obtain other nodes through the `cluster nodes` command.
address = "<redis-master-node>:<redis-port>"
username = "" # keep empty if not using ACL
password = "<password>"  # keep empty if no authentication is required
tls = true
```

4. RedisShake provides a Python script to run RedisShake for all the masters with just one `sync.toml` like the above. This will be available in the `redis-shake` directory from the download done in Step 1
   1. Install the requirements
    ```bash
    cd cluster_helper/
    pip3 install -r requirements.txt
    ``` 
   2. Run the `cluster_helper.py` script
   ```bash
   # Format: python3 cluster_helper.py <path to RedisShake binary> <path to sync.toml>
   python3 cluster_helper.py ../redis-shake sync.toml
   ``` 
   3. Run the above command in the background so all the new data is synced until cutover to the new Redis cluster
   ```bash
   nohup python3 cluster_helper.py ../redis-shake sync.toml &
   ```
5. Login into the target Redis cluster and validate if the keys are synced


This post is only for usage of the sync feature from the RedisShake tool, it offers restore and scan features too. Following the above steps helped us to migrate data between Redis clusters running on K8s.

---
References: <br>
[1] https://redis.io/ <br>
[2] https://www.redhat.com/en/topics/containers/what-is-a-kubernetes-operator <br>
[3] https://redis.io/commands/migrate/ <br>
[4] https://github.com/tair-opensource/RedisShake