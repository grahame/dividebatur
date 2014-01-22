var mod = angular.module('divideBaturServices', []);

mod.factory('countData', ['$http',
    function($http) {
        var cache = {};
        var data_path = function(shortname) {
            return 'data/' + shortname + '.json';
        }
        return {
            'dataPath' : function(shortname) {
                return data_path(shortname);
            },
            'getCount' : function(shortname, cb) {
                if (cache[shortname]) {
                    cb(cache[shortname]);
                } else {
                    $http.get(data_path(shortname)).success(function(data) {
                        cache[shortname] = data;
                        cb(data);
                    });
                }
            }
        }
}]);
