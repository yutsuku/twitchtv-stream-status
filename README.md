# youtube-stream-status

Small Python3 script to check the status of a YouTube live stream.

```
Usage: python3 ./check.py [options] <youtube url>
 -q, --quiet  Do not output anything to stdout
 -w, --wait   Keep polling until the stream starts, then exit
```

## Use case

Automatically start downloading a live stream once it goes online

```
STREAM_URL=<url> python3 ./check.py --wait "$STREAM_URL" && ffmpeg -i $(youtube-dl -g "$STREAM_URL") -c copy stream.ts
```
