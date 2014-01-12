var divideBatur = angular.module('divideBaturControllers', []);
 
divideBatur.controller('CountListCtrl', ['$scope', '$http',
    function ($scope, $http) {
        $http.get('data/count.json').success(function(data) {
            $scope.counts = data;
            $scope.count = $scope.counts[0];
        });
        $scope.count = null;
    }]);

divideBatur.controller('CountDetailCtrl', ['$scope', '$routeParams', '$http',
  function($scope, $routeParams, $http) {
    $http.get('data/' + $routeParams.countId + '.json').success(function(data) {
      $scope.count = data;
    });
  }]);
