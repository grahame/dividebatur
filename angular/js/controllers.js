var divideBatur = angular.module('divideBaturControllers', []);
 
divideBatur.controller('CountListCtrl', function ($scope, $http) {
  $http.get('data/count.json').success(function(data) {
    $scope.counts = data;
    $scope.count = $scope.counts[0];
  });
  $scope.count = null;
});
