#import <Cocoa/Cocoa.h>
#import <Carbon/Carbon.h>
#import <ApplicationServices/ApplicationServices.h>
#import <unistd.h>

int main(int argc, char *argv[]) {
    @autoreleasepool {
        for (int sec = 0; sec < 60; sec++) {
            usleep(1000000); // Wait 1 second between checks

            // 1. Hide CrossOver and Menu Helper
            for (NSRunningApplication *app in [NSWorkspace sharedWorkspace].runningApplications) {
                if ([app.bundleIdentifier isEqualToString:@"com.codeweavers.CrossOver"] ||
                    [app.localizedName containsString:@"Menu Helper"]) {
                    [app hide];
                }
            }

            // 2. Query on-screen windows to find the game window
            CFArrayRef wins = CGWindowListCopyWindowInfo(kCGWindowListOptionOnScreenOnly, kCGNullWindowID);
            if (!wins) continue;

            BOOL found = NO;
            for (NSDictionary *info in (__bridge NSArray *)wins) {
                NSString *owner = info[(id)kCGWindowOwnerName];
                NSNumber *layer = info[(id)kCGWindowLayer];
                NSNumber *pid = info[(id)kCGWindowOwnerPID];

                if (layer.intValue == 0 &&
                    ([owner containsString:@"SHProto"] || [owner containsString:@"Silent"])) {
                    found = YES;
                    pid_t gamePid = (pid_t)pid.intValue;

                    // Bring the game process to the front
                    ProcessSerialNumber psn;
                    if (GetProcessForPID(gamePid, &psn) == noErr) {
                        SetFrontProcessWithOptions(&psn, kSetFrontProcessFrontWindowOnly);
                    }

                    // Hide CrossOver again to ensure it yields foreground focus
                    for (NSRunningApplication *app in [NSWorkspace sharedWorkspace].runningApplications) {
                        if ([app.bundleIdentifier isEqualToString:@"com.codeweavers.CrossOver"]) {
                            [app hide];
                        }
                    }

                    // Click inside the window bounds to activate it and trigger mouse capture
                    NSDictionary *boundsDict = info[(id)kCGWindowBounds];
                    CGRect bounds;
                    if (CGRectMakeWithDictionaryRepresentation((CFDictionaryRef)boundsDict, &bounds)) {
                        CGPoint center = CGPointMake(CGRectGetMidX(bounds), CGRectGetMidY(bounds));
                        CGWarpMouseCursorPosition(center);

                        CGEventRef clickDown = CGEventCreateMouseEvent(NULL, kCGEventLeftMouseDown, center, kCGMouseButtonLeft);
                        CGEventRef clickUp = CGEventCreateMouseEvent(NULL, kCGEventLeftMouseUp, center, kCGMouseButtonLeft);
                        CGEventPost(kCGHIDEventTap, clickDown);
                        CGEventPost(kCGHIDEventTap, clickUp);
                        CFRelease(clickDown);
                        CFRelease(clickUp);

                        CGPoint moved = CGPointMake(center.x + 1, center.y);
                        CGEventRef move = CGEventCreateMouseEvent(NULL, kCGEventMouseMoved, moved, 0);
                        CGEventPost(kCGHIDEventTap, move);
                        CFRelease(move);
                    }
                    break;
                }
            }
            CFRelease(wins);

            if (found) {
                // Ensure focus remains steady while the engine initializes
                for (int rep = 0; rep < 3; rep++) {
                    usleep(1000000);
                    for (NSRunningApplication *app in [NSWorkspace sharedWorkspace].runningApplications) {
                        if ([app.bundleIdentifier isEqualToString:@"com.codeweavers.CrossOver"]) {
                            [app hide];
                        }
                    }
                }
                return 0;
            }
        }
    }
    return 0;
}
