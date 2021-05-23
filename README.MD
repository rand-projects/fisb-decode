*FIS-B Decode* ('fisb-decode') is a back-end system for processing FIS-B
(Flight Information System - Broadcast)
messages transmitted on 978 Mhz, mostly in the United States.
FIS-B
primarily contains meteorlogical information to be used in flight.
This implementation roughly follows the DO-358B standard.

'fisb-decode' is composed of two main parts:

* The capture part of the system ('fisb') is a good way to explore the internal
  structures of FIS-B and can be used as a stand-alone system for this
  purpose. 'fisb' is a multi-level system that turns binary FIS-B messages
  into fully independent weather messages.
* The database part of the system ('harvest') creates .tif images,
  turns vector data into geojson, and manages the FIS-B message-base using
  mongoDB.

'fisb-decode' is strictly a back-end 'meat and potatoes' system.
It does not provide a web-based
interface for humans. It is certainly possible to create front-end systems
using fisb-decode, but fisb-decode is not that system.

FIS-B Decode is not designed, nor intended,
to be used for any purpose other than fun exploration. 

| :warning: WARNING                                                      |
|:-----------------------------------------------------------------------|
| FIS-B Decode is **NOT** intended for actual flight use, nor to be used as a component of a system for any flight related operations (flight planning, etc). It is strictly a fun hobby program with many bugs. It is based loosely on draft standards, not actual standards, and has not undergone any formal testing. **DO NOT USE OTHER THAN FOR FUN-- NOT FLIGHT!!** |


To get started with FIS-B Decode, see the file
'``fisb-decode-intro.pdf``' in the ``fisb-decode/docs`` directory.
