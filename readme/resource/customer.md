# Customers

A customer is an end user of your organization on the BITGEN platform: a person (KYC) or a business (KYB) with a login, an identity file, settings and — once activated and verified — an EUR account, custody wallets, orders and staking positions. `client.customer` creates customers, lists them, and reads or updates an account.

Examples use `client`, a configured `BitgenClient` ([Configuration](../configuration.md)), and `customer`, the `Created` returned by `create()`. A customer is designated by a `UserRef`: their uuid, or a model carrying it — `Created`, `Customer`, `Account` ([User references](../concepts.md#user-references)).

![Activation and identity: from the creation of a customer to the financial resources](../media/activation.svg)

## Methods

| Method | What it does | Returns |
|---|---|---|
| `create(...)` | Creates a customer in your organization and sends them the activation email | `Created` |
| `list(...)` | Lists the customers of your organization | `Page[Customer]` |
| `get(user)` | Reads one account: identity files, details, settings | `Account` |
| `update(user, ...)` | Updates the settings a key may write: theme, locale, notifications | `None` |

Models of this resource, under `bitgen.models`: `Created`, `Customer`, `CustomerAccount`, `AccountAddress`, `CustomerClient`, `CustomerAction`, `CustomerSetup`, `CustomerCollaborations`, `CollaboratorLink`, `ManagerLink`, `CustomerAlert`, `CustomerBusiness`, `Account`, `AccountNotifications`, `Identity` (`KycIdentity`, `KybIdentity`), `KycIdentityForm`, `KybIdentityForm`, `IdentityData`, `IdentityStep`, the `Notifications` input and the `UserRef` alias — and the constant classes `CustomerState`, `IdentityState`, `IdentityMode`, `Locale`, `OrganizationCategory`.

## Create

```
client.customer.create(email: str, manager: str, *, firstname: str | None = None, lastname: str | None = None, fin: str | None = None, needActivation: bool | None = None, notify: bool | None = None, locale: str | None = None, organization: str | None = None) -> Created
```

| Argument | Type | Description |
|---|---|---|
| `email` | `str` | Login of the customer — required |
| `manager` | `str` | uuid of the collaborator of your organization who follows this customer — required; the customer is created in your organization |
| `firstname`, `lastname` | `str \| None` | Optional |
| `fin` | `str \| None` | Tax identification number of the customer — optional, 100 characters max |
| `needActivation` | `bool \| None` | Default `True`: BITGEN emails the customer an activation link and the account stays `CREATED` (the bank, custody, trading and staking resources do not accept it) until they activate. `False`: the account is usable right away and BITGEN sends no email — for an organization that handles activation and notifications with its own system, or through webhooks |
| `notify` | `bool \| None` | Default `True`: the customer receives BITGEN's emails (newsletter). `False`: none |
| `locale` | `str \| None` | `Locale.FR` (default) or `Locale.EN` — anything else is refused before any request |
| `organization` | `str \| None` | Category: `OrganizationCategory.CUSTOMER` (default) or `OrganizationCategory.B2B` — `B2B` also opens a KYB file. `BUSINESS` is reserved to BITGEN administrators: like any other value, the SDK refuses it before any request |

```python
from bitgen.models import Locale, OrganizationCategory

customer = client.customer.create(
    "jean@valjean.fr",
    "MANAGER_UUID",
    firstname="Jean",
    lastname="Valjean",
    locale=Locale.FR,
    organization=OrganizationCategory.B2B,  # a business: a KYB file is opened too — CUSTOMER by default
)

print(customer.uuid)
```

By default the API creates the account and sends the customer an activation email. Until they click it, the account stays `CREATED` (`setup.needActivation` is `True`) and the bank, custody, trading and staking resources do not accept it — only `list`, where it appears as `CREATED`, and `get` see it ([Activation and identity](../concepts.md#activation-and-identity)).

```python
customer = client.customer.create(
    "jean@valjean.fr",
    "MANAGER_UUID",
    needActivation=False,  # you handle onboarding yourself
    notify=False,
)
```

With `needActivation=False` the account is usable right away and BITGEN sends no activation email — for an organization that handles activation and notifications with its own system, or through webhooks; with `notify=False` the customer receives no BITGEN email at all.

When the email already belongs to an active account whose KYC is validated, that account is **attached** to your organization instead of being created. An active account without a validated KYC cannot be attached (`412 user_not_attachable`), an account already attached to another organization is refused (`409 user_already_assigned`), and so is an account still being created, for 15 minutes (`409 account_unavailable`).

Returns a `Created`: the `uuid` of the customer — pass it as is to the other resources.

## List

```
client.customer.list(*, offset: int | None = None, limit: int | None = None, includeClosed: bool | None = None, manager: str | None = None) -> Page[Customer]
```

| Argument | Type | Description |
|---|---|---|
| `offset`, `limit` | `int \| None` | [Pagination](../concepts.md#pagination) |
| `includeClosed` | `bool \| None` | Also returns the `CLOSED` customers — default `False` ([Query booleans](../concepts.md#query-booleans)) |
| `manager` | `str \| None` | Only the customers whose direct manager is this collaborator (uuid) |

```python
page = client.customer.list(offset=0, limit=50)

for item in page.items:
    print(item.login, item.state)  # jean@valjean.fr ENABLED
```

Returns a page of `Customer`:

| Attribute | Description |
|---|---|
| `uuid`, `createdAt` | Identifier and creation time (epoch seconds) |
| `state` | `CustomerState.CREATED` (activation pending), `ENABLED`, `CLOSED` or `FROZEN` — a string; the `CustomerState` constants name the known values |
| `isAvailable` | `False` until the customer has activated their account, then `True` |
| `canLogin` | Whether the customer may sign in to the BITGEN web application |
| `login` | The email |
| `account` | `CustomerAccount`: `email`, `firstname`, `lastname`, `fin` (tax identification number), `birthdate` (date of birth, epoch seconds, or `None`), `phoneZone` and `phoneNumber` (dialing code, `+33` by default, and the number as an integer), `address` (`AccountAddress`: `uuid`, `address`, `state` — the state of the address record — or `None`), `referralCode` (the customer's own referral code, generated at creation) |
| `client` | `CustomerClient`: `roles` (platform roles of the account — always `ROLE_USER` for a customer), `hasTfa` (two-factor authentication enabled), `hasPhishing` (anti-phishing code enabled), `isValid` (`True` once the account has been activated) |
| `action.setup` | `CustomerSetup`: `theme` (theme of the BITGEN web application, `light` by default), `currency` (display currency, `EUR`), `locale` (language of the web application and of the emails: `Locale.FR` or `Locale.EN`), `choosenOrganization` (category chosen at signup: `OrganizationCategory.CUSTOMER`, `B2B` — a string, compare it with the constants), `needActivation` (activation email pending), `notify` (whether the customer accepts BITGEN emails), `onboarding` (whether the web onboarding has been completed) |
| `identity` | The KYC or KYB file of the customer ([Identity](#identity)) |
| `business` | The businesses of the customer, each with its KYB file: a list of `CustomerBusiness` (`identity`) |
| `collaborations.collaborator` | The customer's attachment to your organization, a list of `CollaboratorLink`: `uuid`, `state` (`WAIT` until activation, then `ENABLED`; `REVOKED` once removed), `roles` (`ROLE_USER` for a customer), `organization` (its name), `organizationUuid`, `manager` (uuid of the collaborator in charge of them) |
| `collaborations.manager` | Attachments where this account manages other people — always empty for a customer (a list of `ManagerLink`: `mandate`, `mandatedUntil`: CRM data, not needed for an integration) |
| `alert` | Active compliance alerts, a list of `CustomerAlert`: `uuid`, `state` (`OPEN`, `DECLARATED`, `CONFIRMED`), `severity` (`SUCCESS`, `WARNING`, `CRITICAL`), `sources` (the observations behind the alert — analysis data) |

## Get

```
client.customer.get(user: UserRef) -> Account
```

`user` is the customer, by uuid or by model ([User references](../concepts.md#user-references)).

```python
account = client.customer.get(customer)

print("activation pending" if account.setup.needActivation else "activated")
print(account.identity.state)  # VALIDATED once the verification is done
```

Returns an `Account`:

| Attribute | Description |
|---|---|
| `uuid` | The customer |
| `identity` | The KYC or KYB file of the customer ([Identity](#identity)) |
| `business` | The businesses of the customer, each with its KYB file: a list of `CustomerBusiness` |
| `account` | The same `CustomerAccount` as `Customer`, with `address` reduced to `uuid` and `address` (`state` is `None`) |
| `notifications` | `AccountNotifications` — email preferences: `login` (login-related emails), `newsletter` (BITGEN newsletter) |
| `setup` | The same `CustomerSetup` as `Customer.action.setup`: theme, display currency, language, category chosen at signup, activation pending, BITGEN emails accepted, onboarding completed |

An unknown customer answers `404 unknown_user`.

### Identity

`Identity` is the verification file of a person (`mode` `KYC`) or of a business (`KYB`). The verification itself — questionnaire, documents — is not part of this SDK: read its progress here. Whether a validated identity is required before the financial resources depends on your organization ([Activation and identity](../concepts.md#activation-and-identity)).

| Attribute | Description |
|---|---|
| `uuid` | The file |
| `state` | `IdentityState.CREATED`, `IN_PROGRESS`, `WAIT`, `PENDING`, `VALIDATED`, `REJECTED`, `FROZEN`, `EXPIRED` or `CLOSED` — a string; the `IdentityState` constants name the known values |
| `mode` | `IdentityMode.KYC` or `IdentityMode.KYB` — a string |
| `form` | On a `KycIdentity`, a `KycIdentityForm` — the answers of the KYC questionnaire: `european_residency` (boolean), `ppe` (politically exposed person, boolean), `ppp` (relative of a politically exposed person, boolean), `source_income`, `net_income`, `experience` (crypto experience); plus `score` (internal scoring) and `submittedAt`. On a `KybIdentity`, a `KybIdentityForm`: `activity` (business activity), `score`, `submittedAt` |
| `data.steps` | One `IdentityStep` per step, `status` and `submittedAt` — KYC: `info`, `selfie`, `identity`, `residency`; KYB: `info`, `kbis`, `status`, `domiciliation`, `rbe` |
| `data.verificationUrl` | URL of the identity verification when the provider hosts it, `None` otherwise |
| `data.hosted` | Whether the verification is hosted by the provider (`None` when the API does not say) |
| `data.notifications` | Internal flag |
| `validatedAt`, `expiresAt` | Epoch seconds, or `None` |
| `renewalNotifiedAt` | When the renewal reminder was sent (epoch seconds, or `None`) — an identity expires after 12 months (6 for a politically exposed person) |

`Identity` is a class hierarchy: a `KycIdentity` or a `KybIdentity`, each with its typed `form` — narrow with `isinstance`. A `mode` the SDK does not know yet gives a plain `Identity`, with the common fields only.

```python
from bitgen.models import KybIdentity, KycIdentity

identity = client.customer.get(customer).identity

if isinstance(identity, KycIdentity):
    print(identity.form.source_income)  # salary
elif isinstance(identity, KybIdentity):
    print(identity.form.activity)
```

## Update

```
client.customer.update(user: UserRef, *, theme: str | None = None, locale: str | None = None, notifications: Notifications | None = None) -> None
```

`user` is the customer, by uuid or by model.

| Argument | Type | Description |
|---|---|---|
| `theme` | `str \| None` | Theme of the BITGEN web application (`light` by default) |
| `locale` | `str \| None` | Language of the web application and of the emails: `Locale.FR` or `Locale.EN` — anything else is refused before any request |
| `notifications` | `Notifications \| None` | Email preferences, a dict `{"login": bool, "newsletter": bool}` (both keys optional) — `login` (login-related emails), `newsletter` (BITGEN newsletter) |

```python
from bitgen.models import Locale

client.customer.update(customer, locale=Locale.EN, notifications={"login": True, "newsletter": False})
```

These are the only settings an API key may write — the account details, the identity state and the address are not — and the SDK sends nothing else: an argument left to `None` is not sent. The API answers with an empty body; the method returns `None`.

## Errors

In addition to the [common errors](../errors.md#common-errors):

| Status | `code` | Meaning |
|---|---|---|
| `400` | `invalid_fin` | `fin` (tax identification number) is longer than 100 characters, or not a scalar |
| `403` | `missing_group_organization_or_manager` | `manager` is missing |
| `404` | `unknown_user` | Unknown customer (`get`), or unknown `manager` (`list`) |
| `409` | `user_already_assigned` | The email belongs to an account attached to another organization |
| `409` | `account_unavailable` | The email belongs to an account still being created (less than 15 minutes ago) |
| `412` | `user_not_attachable` | The email belongs to an active account without a validated KYC |
| `422` | `invalid_include_closed` | `includeClosed` is not a boolean value |

## Related

- [User references](../concepts.md#user-references) — uuid or a model with a `uuid`
- [Activation and identity](../concepts.md#activation-and-identity) — what a customer can do before and after activation, and when a validated identity is required
- [Bank accounts](bank.md) — the EUR account of a customer
- [Custody wallets](custody.md) — their crypto wallets
- [Webhooks](webhooks.md) — `user.created` and the `user.identity.*` events
