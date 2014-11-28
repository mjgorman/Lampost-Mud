angular.module('lampost_editor').service('lpCache', ['$q', 'lmBus', 'lmRemote', 'lmUtil',
  function ($q, lmBus, lmRemote, lmUtil) {

    var cacheHeap = [];
    var cacheHeapSize = 32;
    var remoteCache = {};

    var cacheSorts = {
      'room': numericIdSort
    };

    remoteCache.constants = {ref: 0, url: 'constants', sort: angular.noop};

    function cacheEntry(key) {
      var keyParts = key.split(':');
      var keyType = keyParts[0];
      var url = keyType + '/list' + (keyParts[1] ? '/' + keyParts[1] : '');
      var entry = {ref: 0, sort: cacheSorts[keyType] || idSort, url: url};
      remoteCache[key] = entry;
      return entry;
    }

    function cacheKey(model) {
      var cacheKey = (model.dbo_key_type + ':' + model.dbo_id).split(":");
      return cacheKey.slice(0, cacheKey.length - 1).join(':');
    }

    function idSort(values) {
      lmUtil.stringSort(values, 'dbo_id')
    }

    function numericIdSort(values) {
      values.sort(function (a, b) {
        var aid = parseInt(a.dbo_id.split(':')[1]);
        var bid = parseInt(b.dbo_id.split(':')[1]);
        return aid - bid;
      })
    }

    function updateModel(model, outside) {
      var entry = remoteCache[cacheKey(model)];
      if (entry) {
        var cacheModel = entry.map[model.dbo_id];
        if (cacheModel) {
          angular.copy(model, cacheModel);
          lmBus.dispatch('modelUpdate', cacheModel, outside);
        }
      }
    }

    function insertModel(model, outside) {
      var entry = remoteCache[cacheKey(model)];
      if (entry && !entry.promise) {
        if (entry.map[model.dbo_id]) {
          updateModel(model, outside);
        } else {
          entry.data.push(model);
          entry.sort(entry.data);
          entry.map[model.dbo_id] = model;
          lmBus.dispatch('modelCreate', entry.data, model, outside);
        }
      }
    }

    function deleteEntry(key) {
      var heapIx = cacheHeap.indexOf(key);
      if (heapIx > -1) {
        cacheHeap.splice(headIx, 1);
      }
      delete remoteCache[key];
    }

    function deleteModel(model, outside) {
      var entry = remoteCache[cacheKey(model)];
      if (entry && !entry.promise) {
        var cacheModel = entry.map[model.dbo_id];
        if (cacheModel) {
          entry.data.splice(entry.data.indexOf(cacheModel), 1);
          delete entry.map[model.dbo_id];
          lmBus.dispatch('modelDelete', entry.data, model, outside);
        }
      }
      var deleted = [];
      angular.forEach(remoteCache, function (entry, key) {
        var keyParts = key.split(':');
        if (keyParts[1] === model.dbo_id) {
          deleted.push(key);
        }
      });
      angular.forEach(deleted, function (key) {
        deleteEntry(key);
      });
    }

    lmBus.register('edit_update', function (event) {
      var outside = !event.local;
      switch (event.edit_type) {
        case 'update':
          updateModel(event.model, outside);
          break;
        case 'create':
          insertModel(event.model, outside);
          break;
        case 'delete':
          deleteModel(event.model, outside);
          break;
      }
    });

    this.invalidate = function (key) {
      deleteEntry(key)
    };

    this.cacheValue = function (key, dbo_id) {
      return remoteCache[key].map[dbo_id];
    };

    this.deref = function (key) {
      if (!key) {
        return;
      }
      var entry = remoteCache[key];
      if (!entry) {
        return;
      }
      entry.ref--;
      if (entry.ref === 0) {
        cacheHeap.unshift(key);
        for (var i = cacheHeap.length; i >= cacheHeapSize; i--) {
          var oldEntry = remoteCache[cacheHeap.pop()];
          delete oldEntry.map;
          delete oldEntry.data;
        }
      }
    };

    this.cache = function (key) {
      var entry = remoteCache[key] || cacheEntry(key);
      if (entry.data) {
        if (entry.ref === 0) {
          cacheHeap.splice(cacheHeap.indexOf(key), 1);
        }
        entry.ref++;
        return $q.when(entry.data);
      }

      if (entry.promise) {
        entry.ref++;
        return entry.promise;
      }
      entry.promise = lmRemote.request('editor/' + entry.url).then(function (data) {
        delete entry.promise;
        entry.ref++;
        entry.data = data;
        entry.map = {};
        for (var i = 0; i < data.length; i++) {
          entry.map[data[i].dbo_id] = data[i];
        }
        entry.sort(entry.data);
        return $q.when(entry.data);
      });
      return entry.promise;
    };

}]);