fisb package
============


The ``fisb`` package consists of several levels that progressively
process FIS-B messages. This implies that the
output from one level is the input of the next level.
The progressive levels consist of:

- **level0:** This is the basic level that takes a hex stream generated
  by FlightAware's version of dump978_.
  It generates a json message which is sent to standard output, usually
  to be fed to **level1**. However, *level0* is useful by itself if you
  are interested in looking at the structure of FIS-B messages. There
  are configuration options at this level that will show all the contents
  of the message, including reserved fields.

- **level1:** This level is concerned about taking segmented and TWGO
  (Text With Graphic Overlay) messages and doing the correct things with
  them. Sometimes large messages are sent in segmented form-- they are
  too big for a single message and must be sent in parts. *level1*
  looks for all the parts, puts them together and sends them as a
  single message. TWGO messages are messages that have a graphic part
  and a text part. These will come at different times and need to be
  matched up and sent as a single message. Well, that's the basic concept
  anyway. It's more complicated than that. The *level1* documentation has
  more details.

- **level2:** This level takes the completed messages from *level1* and
  turns them into a finished product. I tend to think of this as the
  message you *wish* FIS-B had sent. Text and graphic parts are put back
  together, every message has an expiration time (this is another sounds
  simple concept that isn't), and all times are complete ISO times (not
  FAA's approximation of a time).

- **level3:** FIS-B sends most messages repetitively at set intervals.
  This implies that programs acting on a message will need to reprocess
  the same message more than once, maybe many times. In order to
  decrease this processing time down the road, *level3* takes a message
  digest of each message and won't send it out if it hasn't changed. But
  like most things FIS-B, it's more complicated.

There are a couple of modules that feed data into the system, but in
different ways:

- **levelNet:** This is an optional level if you are feeding ``fisb-decode``
  with live data from a server, rather than from a file. It will connect
  to your acquisition system (usually *dump978* running in server
  mode).

- **levelStratux:** This is an optional level if you are feeding ``fisb-decode``
  with live data from a Stratux box, rather than from a file or *dump978*.
  Actually, Stratux uses another dump978 program and converts FIS-B to
  GDL format. ``levelStratux`` then converts it back to dump978 format.
  If you use this, it is critical that your computer has somewhat accurate
  clock (within 30 seconds or so) as Stratux doesn't provide clock data to
  the messages. The local clock on the machine you are using provides the source.

- **trickle:** Trickle is a program used for testing. Primarily for the
  official series of test groups and a few tests I added. Trickle will
  read a set of messages and pretend that they are being read at the
  time they were actually received. It has a mechanism to communicate
  with Harvest (the database manager) to get it on the same time
  basis also. So if you have a set of messages that took place over
  an hour, trickle will trickle them out over an hour. It's essentially
  a time machine back to the past (or future: there are some test messages
  that as the time I write this were set in the future).

.. _dump978: https://github.com/flightaware/dump978

.. toctree::
   :maxdepth: 4

   fisb.level0
   fisb.level1
   fisb.level2
   fisb.level3
   fisb.levelNet
   fisb.levelStratux
   fisb.trickle
