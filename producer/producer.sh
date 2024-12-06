#!/bin/bash

content_size=1M
content_name=/random
router_addr=tcp4://172.16.232.85

cleanup(){
  echo "Cleaning up..."
  docker rm -f producer
}

trap cleanup EXIT

docker run -dit --name producer -e NDN_CLIENT_TRANSPORT=$router_addr hydrokhoos/ndn-all
docker exec producer bash -c "ndnsec key-gen /producer | ndnsec cert-install -"
docker exec producer bash -c "dd if=/dev/urandom of=/random.bin bs=$content_size count=1 status=none"
echo -e "Publishing Content...\nName: $content_name\nSize: $content_size"
docker exec producer bash -c "ndnputchunks $content_name < /random.bin"
