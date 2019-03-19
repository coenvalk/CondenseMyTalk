# CondenseMyTalk
Automatic video lecture summarizing platform

## Background
For students with learning differences such as attention deficit disorder and ADHD,
sitting and focusing on one topic for hours is a great challenge, causing students
to get distracted, uninterested, and fall behind in class. Lecture notes offer a condensed
form of the lecture, but students that learn best through audio/visual stimulation have difficulty
retaining information in this way. CondenseMyTalk is a platform that automatically creates
lecture summaries from longer videos, that condenses the information of the two hour lecture
into a 5 to 10 minute video.

CondenseMyTalk's philosophy is that every part of the video has an importance value attached to it.
To make a good quality lecture summary, one must find the most important parts of the lecture and stitch
those parts together. CondenseMyTalk makes use of two main methods to determine the "importance" of a part of a video:
User comments, and summaries created by a transcript of the video. Users can upvote and downvote parts
of the video, along with appending supplementary information to the video. CondenseMyTalk records at
what part of the video you upvote or downvote, and considers that to be a "region of interest" - if the
part of the video was upvoted, that part is considered more important. If that part of the video is
downvoted, that part is considered less important. CondenseMyTalk also makes use of the Google Cloud
Speech-to-text API to create a full transcript of the video, which is fed into a text summary creator,
and the parts of the video that are included in that summary are also considered important. Lastly, parts
of the video are added to the summary in order of importance to create a lecture summary video.

## Usage
CondenseMyTalk is made in Python 3 with Django. This project also makes use of the Google Cloud speech-to-text API to 
create lecture transcripts. Create an account with Google Cloud and include the API as Python environment variables to
make use of that functionality. Additionally, install all required python libraries in requirements.txt. Once this is
complete, start the Django server to begin a version of the platform.

## TODO
For future work I would like to incorporate optical character recognition that can analyze the importance of a certain frame and take that
into account in the importance curve of the video. Additionally, the two aspects of the program that take the largest amount of compute
time is creating a transcript - which is a necessary evil - and exporting the condensed video together. Possibly, instead of creating an
entirely new video, to scrub through the existing video as the video continues.
