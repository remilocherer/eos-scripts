# EOS Scripts

Various scripts for Arista EOS

## RouteTracker

Next-hops for static routes can be tracked with [BFD](https://www.arista.com/en/support/toi/eos-4-20-1f/13939-bfd-for-static-routes). In some situations it is desirable to track a next-hop (or another IP address) with ICMP. 

With the "monitor connectivity" feature EOS is able to check connectivity for a given IP address. The RouteTracker shell script leverages this to add or remove a static route based on the packet-loss number reported by monitor connectivity. All config data is stored in the main EOS config either in a daemon or monitor connectivity section.

Another approach is documented here: https://arista.my.site.com/AristaCommunity/s/article/ip-static-route-with-health-check
