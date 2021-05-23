Miscellaneous Files related to dump978-fa

fadump-sdrplay
	Bash script to execute dump978-fa on SDRPLAY RSP1A.

fadump-sdrplay-server
	Same as above but executes in server mode.

Patches:

Both of the following patches are optional.

The source I used to apply the patches to is FlightAware 978
Release 5.0.

GitHub commit 'c1e37f4acd7e47c46ca312a4016128aecfd03630'.

soapy_source.cc.patch
	SDRPLAY RSP1A does not work out of the box.
	If you are using the SDRPLAY (much better decode
	rate than AirSpy or RTLSDR) apply this patch.
	
	cd to the dump978 directory:

	   patch -u soapy_source.cc -i soapy_source.cc.patch

demodulator.cc.patch
        Dump978 out of the box determines a slicing level and
        uses it. If it works, it works, if it doesn't, it doesn't.
        When you have a good signal, that's all you need. For
        weak signal work (I use a 15 element beam from 6 miles
        away) you need all the help you can get.

        What this mod does is to detect a failure to decode. When it
        does, it starts trying different slicing levels, some higher,
        some lower until it gets a successful decode. It
        substantially increases the decode rate when the signal is
        weak (think rain, etc). You will occasionally get a LEVEL0.ERR
        for a bad decode that passed FEC checks, but it's rare.

        On a day with very good receive conditions, this patch will
        decode 12-16 packets/min that I would have otherwise missed. On
        my 3 packets/sec medium ground station that's 4-5 seconds of
        data every minute.

        If you get RSRs of 100 all the time, you don't need this patch.
        
        There is a processor time cost for this. This mod will
        turn off all UAT processing. Only FIS-B packets get through.

        cd to the dump978 directory:

           patch -u demodulator.cc -i demodulator.cc.patch
