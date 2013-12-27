from rest_framework import serializers
from django.utils.translation import ugettext as _

class UploadPolicyConditionField(serializers.RelatedField):
    '''
    A condition is in one of three formats:
      - ["content-length-range", 1048579, 10485760]
      - ["starts-with", "$key", "user/eric/"]

    http://docs.aws.amazon.com/AmazonS3/latest/dev/HTTPPOSTForms.html#HTTPPOSTConstructPolicy
    '''
    def to_native(self, value):
        pass

    def from_native(self, data):
        if isinstance(data, list):
            return self.from_native_list(data)
        elif isinstance(data, dict):
            return self.from_native_dict(data)
        else:
            from django.core.exceptions import ValidationError
            raise ValidationError(
                _('Condition must be array or dictionary: %(condition)s'),
                params={'condition': data},
            )

    def from_native_list(self, condition_list):
        '''
        These arrive in one of three formats:
          - ["content-length-range", 1048579, 10485760]
          - ["content-length-range", 1024]
          - ["starts-with", "$key", "user/eric/"]

        Returns an object with these attributes set:
          - operator: 'eq', 'starts-with', or None
          - key: 'content-length-range', 'key', etc.
          - value: "user/eric/", 1024, or None
          - value_range: [1048579, 10485760] or None
        '''
        from numbers import Number
        from django.core.exceptions import ValidationError
        from s3_upload.models import UploadPolicy
        original_condition_list = condition_list # We use this for error reporting
        condition_list = list(condition_list)
        for item in condition_list:
            if not isinstance(item, basestring) and not isinstance(item, Number):
                raise ValidationError(
                    _('Values in condition arrays should be numbers or strings'),
                )
        try:
            if condition_list[0] in ['eq', 'starts-with']:
                operator = condition_list.pop(0)
            else:
                operator = None
        except IndexError:
            raise ValidationError(
                _('Not enough values in condition array: %(condition)s'),
                params={'condition': original_condition_list},
            )
        try:
            key = condition_list.pop(0)
        except IndexError:
            raise ValidationError(
                _('Missing key in condition array: %(condition)s'),
                params={'condition': original_condition_list},
            )
        if key.startswith('$'):
            key = key[1:]
        else:
            raise ValidationError(
                _('Key in condition array should start with $: %(key)s'),
                params={'key': current},
            )
        if len(condition_list) == 0:
            raise ValidationError(
                _('Missing values in condition array: %(condition)s'),
                params={'condition': original_condition_list},
            )
        elif len(condition_list) == 1:
            value = condition_list.pop(0)
            value_range = None
        elif len(condition_list) == 2:
            value = None
            value_range = condition_list
        else:
            raise ValidationError(
                _('Too many values in condition array: %(condition)s'),
                params={'condition': original_condition_list},
            )
        return UploadPolicy(
            operator=operator,
            key=key,
            value=value,
            value_range=value_range
        )

    def from_native_dict(self, condition_dict):
        '''
        {"bucket": "name-of-bucket"}
        '''
        pass

class UploadPolicySerializer(serializers.Serializer):
    '''
    http://docs.aws.amazon.com/AmazonS3/latest/dev/HTTPPOSTForms.html#HTTPPOSTConstructPolicy
    '''
    expiration = serializers.DateTimeField()
    conditions = UploadPolicyConditionField(many=True, read_only=False)