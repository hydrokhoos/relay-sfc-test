#!/bin/bash

content_name=/rand-relay/random
router_addr=tcp4://172.16.232.85

cleanup(){
  echo "Cleaning up..."
  docker rm -f consumer
}

trap cleanup EXIT

docker run -dit --name consumer -e NDN_CLIENT_TRANSPORT=$router_addr hydrokhoos/ndn-all
docker exec consumer bash -c "ndnsec key-gen /consumer | ndnsec cert-install -"
echo "Getting content $content_name ..."
docker exec consumer bash -c "ndncatchunks -f $content_name > /res.bin"
docker cp consumer:/res.bin .
