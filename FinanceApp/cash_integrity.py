"""Save guards for paired records. No data migrations or automatic repairs."""
from functools import wraps
from django.core.exceptions import ValidationError
from django.db import router, transaction

LINK_FIELDS = ('expense_id', 'collection_id', 'loan_disbursement_id', 'fund_transaction_id')


def require_cash_link(instance, link, using=None, lock=False):
    from .models import CashTransaction
    db = using or router.db_for_write(type(instance), instance=instance)
    qs = CashTransaction.objects.using(db)
    if lock:
        qs = qs.select_for_update()
    cash = qs.filter(**{link + '_id': instance.pk}).first()
    if cash is None:
        raise ValidationError(
            'This existing record has no linked cash transaction. '
            'Saving is blocked to avoid creating another debit or credit. '
            'Review and reconcile its existing records first.'
        )
    if sum(getattr(cash, field) is not None for field in LINK_FIELDS) != 1:
        raise ValidationError('The cash transaction has conflicting source links. Review it before saving.')
    return cash


def atomic_cash_save(link):
    def decorate(save):
        @wraps(save)
        def wrapped(self, force_insert=False, force_update=False, using=None, update_fields=None):
            db = using or router.db_for_write(type(self), instance=self)
            if update_fields is not None:
                update_fields = frozenset(update_fields)
                if not update_fields:
                    return
            original_pk, original_adding, original_db = self.pk, self._state.adding, self._state.db
            try:
                with transaction.atomic(using=db):
                    existing = None
                    if self.pk is not None:
                        existing = type(self)._base_manager.using(db).select_for_update().filter(pk=self.pk).first()
                    if existing is not None:
                        require_cash_link(self, link, using=db, lock=True)
                    elif not self._state.adding:
                        raise ValidationError('This record was deleted. Reload the page instead of recreating it.')
                    # Partial disbursement saves must calculate from the values actually being saved.
                    if link == 'loan_disbursement' and update_fields is not None:
                        if existing is not None:
                            for field in ('principal_amount', 'commission_percent'):
                                if field not in update_fields:
                                    setattr(self, field, getattr(existing, field))
                        update_fields |= {'commission_amount', 'disbursed_amount'}
                    return save(self, force_insert=force_insert, force_update=force_update,
                                using=db, update_fields=update_fields)
            except Exception:
                if original_adding:
                    self.pk, self._state.adding, self._state.db = original_pk, original_adding, original_db
                    self._state.fields_cache.pop('cash_transaction', None)
                raise
        return wrapped
    return decorate
