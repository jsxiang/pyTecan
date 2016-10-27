# Find log files related to .gem file in current directory
LOGDIR=../../logs
for f in *.gem
do
    tag=$(grep Generated $f | sed -e 's/.*(\([^)]*\)).*/\1/')
    echo $f : $tag
    grep -l "$tag" $LOGDIR/*.log
done
