from lampost.client.handlers import MethodHandler, SessionHandler
from lampost.context.resource import m_requires
from lampost.datastore.classes import get_dbo_class
from lampost.datastore.dbo import Untyped
from lampost.datastore.exceptions import DataError


m_requires(__name__, 'log', 'datastore', 'dispatcher', 'perm', 'edit_update_service')

obj_defaults = {}


class Editor(MethodHandler):
    parent_type = None

    def initialize(self, obj_class, imm_level='admin'):
        self.obj_class = obj_class
        self.imm_level = imm_level
        self.dbo_key_type = obj_class.dbo_key_type

    def list(self):
        return [edit_dto(self.session.player, obj) for obj in load_object_set(self.obj_class)]

    def create(self):
        self.raw['owner_id'] = self.session.player.dbo_id
        self.pre_create()
        new_obj = create_object(self.obj_class, self.raw)
        self.post_create(new_obj)
        return publish_edit('create', new_obj, self.session)

    def delete(self):
        del_obj = load_object(self.obj_class, self.raw['dbo_id'])
        if not del_obj:
            raise DataError('Gone: Object with key {} does not exist'.format(raw['dbo_id']))
        check_perm(self.session, del_obj)
        self.pre_delete(del_obj)
        holder_keys = fetch_set_keys('{}:holders'.format(del_obj.dbo_key))
        for dbo_key in holder_keys:
            cached_holder = load_cached(dbo_key)
            if cached_holder:
                save_object(cached_holder)
        delete_object(del_obj)
        for dbo_key in holder_keys:
            reloaded = reload_object(dbo_key)
            if reloaded:
                publish_edit('update', reloaded, self.session, True)
        self.post_delete(del_obj)
        publish_edit('delete', del_obj, self.session)

    def update(self):
        existing_obj = load_object(self.obj_class, self.raw['dbo_id'])
        if not existing_obj:
            raise DataError("GONE:  Object with key {} no longer exists.".format(self.raw['dbo.id']))
        check_perm(self.session, existing_obj)
        self.pre_update(existing_obj)
        update_object(existing_obj, self.raw)
        self.post_update(existing_obj)
        return publish_edit('update', existing_obj, self.session)

    def metadata(self):
        return {'parent_type': self.parent_type, 'new_object': get_dbo_class(self.dbo_key_type)().dto_value}

    def test_delete(self):
        return ['{} - {}'.format(dbo_id) for dbo_id in fetch_set_keys('{}:{}_holders'.format(self.dbo_key_type, self.raw['dbo_id']))]

    def pre_delete(self, del_obj):
        pass

    def post_delete(self, del_obj):
        pass

    def pre_create(self):
        pass

    def post_create(self, new_obj):
        pass

    def pre_update(self, existing_obj):
        pass

    def post_update(self, existing_obj):
        pass


class ChildList(SessionHandler):
    def initialize(self, obj_class):
        self.obj_class = obj_class
        self.dbo_key_type = obj_class.dbo_key_type
        self.parent_type = obj_class.dbo_parent_type

    def main(self, parent_id):
        set_key = '{}_{}s:{}'.format(self.parent_type, self.dbo_key_type, parent_id)
        self._return([edit_dto(self.session.player, obj) for obj in load_object_set(self.obj_class, set_key)])


class ChildrenEditor(Editor):
    def initialize(self, obj_class, imm_level='admin'):
        super().initialize(obj_class, imm_level)
        self.parent_type = obj_class.dbo_parent_type

    def _check_perm(self, obj):
        check_perm(self.session, find_parent(obj, self.parent_type))

    def pre_delete(self, del_obj):
        self._check_perm(del_obj)

    def pre_create(self):
        self._check_perm(self.raw)

    def pre_update(self, existing_obj):
        self._check_perm(existing_obj)


def find_parent(child, parent_type=None):
    try:
        dbo_id = child.dbo_id
        parent_type = child.dbo_parent_type
    except AttributeError:
        dbo_id = child['dbo_id']
    parent = load_object(get_dbo_class(parent_type), dbo_id.split(':')[0])
    if not parent:
        raise DataError("Parent Missing")
    return parent
