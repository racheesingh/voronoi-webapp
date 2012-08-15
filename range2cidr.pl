#! /usr/bin/perl -w

# Description: Take a list of ranges and convert to CIDR.
#
# Execution:
#
#  perl range2cidr.pl
#
# Input format: list of ranges, one per line (other lines are ignored)
#
# Example:
#
#  echo '10.0.0.1 - 10.16.255.253' | perl range2cidr.pl
#  
# Details:
#
# Each range is converted to the minimal list of CIDR blocks.

use strict;
use English;
use IO::Socket;

# convert from IP to number
sub ip2num {
    my ($ip) = @_;
    return unpack("N", inet_aton($ip));
}

# convert from number to IP
sub num2ip {
    my ($num) = @_;
    return inet_ntoa(pack("N", $num));
}

# convert a range to prefixes
sub find_prefixes
{
    my ($lo, $hi) = @_; 
    
    my @prefixes;

    if (($lo == 0) && ($hi == 0xFFFFFFFF)) {
        # 0.0.0.0/0 is a special-case, as the loop never exits for it
        push(@prefixes, [ 0, 0 ]);
    } else {
        # extract the prefixes out one at a time
        my $addr = $lo;
        my $bit = 0;
        my $mask = 0; 
        while ($addr <= $hi) {
            $mask |= (1 << $bit);
            if (($addr & $mask) || (($addr | $mask) > $hi)) {
                push(@prefixes, [ $addr, (32 - $bit) ]);
                $addr += (1 << $bit);
                $bit = 0;
                $mask = 0;
            } else {
                $bit++;
            }
        }
    }

    return @prefixes;
}



##
## main program begins here
##

while (<>) {
    my ($lo, $hi);
    if (/^\s*(\d+\.\d+\.\d+\.\d+)\s*-\s*(\d+\.\d+\.\d+\.\d+)\s*$/) {
        ($lo, $hi) = (ip2num($1), ip2num($2));
        if (defined($lo) && defined($hi)) {
            foreach my $prefix (find_prefixes($lo, $hi)) {
                print num2ip($prefix->[0]), "/", $prefix->[1], "\n";
            }
        }
    }
    unless (defined($lo) && defined($hi)) {
        print;
    }
}

