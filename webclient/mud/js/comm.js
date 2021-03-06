angular.module('lampost_mud').service('lmComm', ['lpEvent', 'lpData', 'lpRemote', 'lpDialog', function (lpEvent, lpData, lpRemote, lpDialog) {

    var self = this;
    var allLogins = false;
    lpEvent.register('friend_login', friendLogin);
    lpEvent.register('any_login', anyLogin);
    lpEvent.register('login', checkAllLogins);
    lpEvent.register('logout', function() {
        checkAllLogins();
    });
    lpEvent.register('notifies_updated', checkAllLogins);

    function checkAllLogins() {
        if (lpData.notifies.indexOf('allDesktop') > -1 || lpData.notifies.indexOf('allSound') > -1) {
            if (!allLogins) {
                lpRemote.registerService('login_notify_service');
                allLogins = true;
            }
        } else {
            if (allLogins) {
                allLogins = false;
                lpRemote.unregisterService('login_notify_service');

            }
        }
    }

    function friendLogin(friend_info) {
        if (lpData.notifies.indexOf('friendDesktop') > -1 && lpData.notifies.indexOf('allDesktop') == -1) {
            self.notify({icon: 'image/friendNotify.png', title: "Your friend " + friend_info.name + " logged into " + lampost_config.title, content: ''});

        }
        if (lpData.notifies.indexOf('friendSound') > -1 && lpData.notifies.indexOf('allSound') == -1) {
            jQuery('#sound_beep_ping')[0].play();

        }
        lpEvent.dispatch('display_line', 'Your friend ' + friend_info.name + ' just logged in', 'system');
    }

    function anyLogin(login) {
        if (lpData.notifies.indexOf('allDesktop') > -1) {
            self.notify({icon: 'image/friendNotify.png', title: "Player " + login.name + " logged into " + lampost_config.title, content: ''});
        }

        if (lpData.notifies.indexOf('allSound') > -1) {
            jQuery('#sound_beep_ping')[0].play();
            lpEvent.dispatch('display_line', login.name + ' just logged in', 'system');
        }

    }

    function showNotification(notify_data) {
        var notification = window.webkitNotifications.createNotification(notify_data.icon, notify_data.title, notify_data.content);
        notification.show();
    }

    this.requestNotificationPermission = function (notify_data) {
        lpDialog.showConfirm("Allow Notifications", "You must grant permission to allow notifications from " + lampost_config.title).then(function () {
            window.webkitNotifications.requestPermission(function () {
                self.notify(notify_data);
            })
        });
    };

    this.notify = function (notify_data) {
        if (!window.webkitNotifications) {
            return;
        }
        var permLevel = window.webkitNotifications.checkPermission();
        if (permLevel == 0) {
            showNotification(notify_data);
        } else if (permLevel == 1) {
            self.requestNotificationPermission(notify_data);
        }
    }

}]);
