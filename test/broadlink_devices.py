import broadlink
broadlink.setup('myssid', 'mynetworkpass', 3)
devices = broadlink.discover()
print(devices)
