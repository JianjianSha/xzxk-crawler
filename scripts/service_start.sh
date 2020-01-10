source activate

# do deployment automatically, including 
#  1. pull newest codes
#  2. prepare environment
#  2. modify configuration
#  3. launch task
#  4. and so on..
# add port num behind if 80 is used already
python './service_start.py' 8181