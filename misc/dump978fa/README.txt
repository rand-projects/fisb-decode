*** Note: The FIS-B 978 demodulator is now preferred over
*** dump978-fa because of its superior performance.

Miscellaneous Files related to dump978-fa

fadump-sdrplay
	Bash script to execute dump978-fa on SDRPLAY RSP1A.

fadump-sdrplay-server
	Same as above but executes in server mode.

Patches:

The soapy_source patch is MANDITORY if using an RSP1A. Not needed
for other SDRs.

The source I used to apply the patches to is FlightAware 978
Release 5.0.

GitHub commit 'c1e37f4acd7e47c46ca312a4016128aecfd03630'.

soapy_source.cc.patch
	SDRPLAY RSP1A does not work out of the box with FlightAware
	dump978-fa.
	If you are using the SDRPLAY (much better decode
	rate than AirSpy or RTLSDR) apply this patch.
	
	cd to the dump978 directory:

	   patch -u soapy_source.cc -i soapy_source.cc.patch

