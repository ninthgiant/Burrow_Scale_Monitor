# README for Arduino Project: AD7193_v035_commonCode and AD7193_MOM_v01

This project began as code common with the Arduino project HX711_R4_R3_v02 which runs on both the Uno Rev3 and Uno Rev4 using either HX711 or AD7193 amplifiers.

As of June 5, 2024, this code assumes the Arduino R4 Minima platform and the AD7193 amplifier. AD7193-specific code based on sample code from [Tacuna Systems](https://tacunasystems.com) and works with the following setup: Arduino R4 minima, Adafruit SD board, RTC_DS1307 version, PRDC_AD7193 driving and AD7193 on the Tacuna built shield with LCD screen.

Code assumes you use the version of the PRDC_AD7193.h and .cpp included here which makes changes to allow for the R4 minima to work correctly with this configuration.

As of June 4, 2024, renamed as AD7193_MOM_v01 because this is no longer beta, but is production. This code uploaded to all Kent Island bound R4 Arduinos for use in summer 2024 season. 

NOTE: "MOM" stands for "Mass-O-Matic", the working name for the Burrow Scale Monitor
