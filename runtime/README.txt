Runtime files and other created files are kept inside
the directories here. The contents of these directories are
usually safe to remove when the parts that create them are not
running.

Do not remove the README.txt files, they are there for git to make
the directory. Any other file is fair game.

images
	.png images created by harvest. The .png files will be
	wiped out at the start of each run.

web-images
	.png images created by harvest. The .png files will be
	wiped out at the start of each run. These are the files
	served to the web. They are copies of 'images' files,
	but have different names, so that each message is associated
	with a unique file removing any chance of accessing a file
	being changed.
	
misc
	Misc files. If enabled, PIREPs that can't be decoded are
	saved here. 'sync.fisb' is also stored here.

harvest
	Where level2 messages are sent waiting for harvest to
	read them.

msg-archive
	If set in level0Config, all messages will be archived here,
	one file per day. It grows quickly, so beware.
