"""Level2 configuration information.

"""

#: Filename used to record frames that error out during decoding.
ERROR_FILENAME = 'LEVEL2.ERR'

#: Number of minutes after a METAR observation time to expire the METAR.
#: There is no set time in the standard, so this is usually set to 120
#: which is twice the time you would expect a new message.
METAR_EXPIRATION_MINUTES = 120

#: Number of minutes after a ``FIS-B PRODUCTS UNAVAILABLE`` message comes in to expire it.
#: The standard states these should be expired 20 minutes after the last
#: received time. These don't get stored by level 3. Best to leave at 20.
FISB_EXPIRATION_MINUTES = 20

#: ISO-8601 date to use for PERM NOTAMs.
#: We use 1/1/2038 which is 19 days before 32-bit Unix time runs out.
#: We usually use the PERM time for fields like 'valid until'. We don't
#: use this as an expiration time.
NOTAM_PERM_TIME = '2038-01-01T00:00:00Z'

#: Time in minutes to expire Service Status message.
#: Should be refreshed by a new message every 20 seconds, so 40
#: seconds is set as the expiration time.
SERVICE_STATUS_EXPIRATION_SECONDS = 40

#: Regional NEXRAD expire time.
#: Standard says 75 minutes.
#: NOTE: Harvest has its own image expiration system.
#: *This config value is essentially ignored in Harvest.*
REGIONAL_NEXRAD_EXPIRATION_MINUTES = 75

#: CONUS NEXRAD expire time.
#: Standard says 75 minutes.
#: NOTE: Harvest has its own image expiration system.
#: *This config value is essentially ignored in Harvest.*
CONUS_NEXRAD_EXPIRATION_MINUTES = 75

#: Turbulence message expire time.
#: Standard says 105 minutes.
#: NOTE: Harvest has its own image expiration system.
#: *This config value is essentially ignored in Harvest.*
TURBULENCE_EXPIRATION_MINUTES = 105

#: Icing message expire time.
#: Standard says 105 minutes.
#: NOTE: Harvest has its own image expiration system.
#: *This config value is essentially ignored in Harvest.*
ICING_EXPIRATION_MINUTES = 105

#: Cloud tops message expire time.
#: Standard says 105 minutes.
#: NOTE: Harvest has its own image expiration system.
#: *This config value is essentially ignored in Harvest.*
CLOUD_TOPS_EXPIRATION_MINUTES = 105

#: Lightning message expire time.
#: Standard says 75 minutes.
#: NOTE: Harvest has its own image expiration system.
#: *This config value is essentially ignored in Harvest.*
LIGHTNING_EXPIRATION_MINUTES = 75

#: Number of minutes after which a PIREP should expire
#: after its last reception.
#: For standard compliance, should be at > 75 minutes.
#: If you are using the report time to expire, 120 minutes
#: is a fair choice (so a PIREP lives for 2 hours after the
#: report time). If you are using time after last reception,
#: use something close to 75 (like 76).
PIREP_EXPIRATION_MINUTES = 120

#: Use the report time rather than the received time for
#: expiring PIREPs. For standard compliance set this to
#: ``False``. If you use this in conjunction with Harvest,
#: expect to get a lot of ``*DOA*`` messages. The FAA can keep
#: PIREPs around for a LONG time (like 4 hours).
PIREP_USE_REPORT_TIME_TO_EXPIRE = True

#: Default TWGO option for expiration time if no
#: better options exist. The minimum retention time after
#: last reception is 60 minutes (this is what the standard
#: requires if there is no explicit stop time in the message).
#: Keep this value at least 61.
TWGO_DEFAULT_EXPIRATION_TIME = 61

#: Bypass any smart expiration times for TWGO messages and
#: set expiration times at least 60 minutes in the future.
#: This is the classic 'retain until not sent for at least 60 minutes.'
#: The standard also states that you can use the message
#: stop time, but some test writers understand this and some
#: don't. Some test messages are broken in this regard.
#: Make sure this is ``True`` when testing (except TG20).
#: TG20 will fail if you don't have this set to ``False``,
#: because it doesn't retransmit the messages like would happen in actual use.
#:
#: For general use, set this to ``False`` (i.e. use 'smart expiration').
#: It allows actual best stop dates to be used including NOTAM parsed dates.
#: If a message doesn't have a stop date, it will fall back to the 'at least 60
#: minutes rule'. If a message has multiple records with different stop dates,
#: it will pick the latest one.
BYPASS_TWGO_SMART_EXPIRATION = False
