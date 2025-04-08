[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/integration)

Этот репозиторий содержит настраиваемый компонент для Home Assistant для отображения данных со счетчиков, зарегистрированных в сервисе [Тайпит](https://cloud.meters.taipit.ru/).

Работа интеграции проверена на однофазных счетчиках [НЕВА МТ 114 AS WF1P](https://www.meters.taipit.ru/catalog/neva/odnofaznyie-schetchiki/mnogotarifnyie/2929/) и трехфазных [НЕВА МТ 315](https://www.meters.taipit.ru/catalog/neva/trehfaznyie-schetchiki/mnogotarifnyie/3281/)

![НЕВА МТ 114 AS WF1P](images/neva_mt_114_as_wf1p_3.png) ![НЕВА МТ 315](images/neva_mt_315_1.0_AR_GSM1BSCP28-2.png)

# Установка

**Способ 1.** Через [HACS](https://hacs.xyz/) > Интеграции > Добавить пользовательский репозиторий > https://github.com/lizardsystems/hass-taipit/ > **Taipit** > Установить

**Способ 2.** Вручную скопируйте папку `taipit` из [latest release](https://github.com/lizardsystems/hass-taipit/releases/latest) в директорию `/config/custom_components`.

# Настройка

> [Настройки](https://my.home-assistant.io/redirect/config) > Устройства и службы > [Интеграции](https://my.home-assistant.io/redirect/integrations) > [Добавить интеграцию](https://my.home-assistant.io/redirect/config_flow_start?domain=taipit) > Поиск `Taipit`

или нажмите:

[![Добавить интеграцию](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start?domain=taipit)

![Установка taipit](images/setup-1.jpg)

Появится окно настройки.

Укажите логин и пароль учетной записи на сервисе [Тайпит](https://cloud.meters.taipit.ru/).

Для тестирования вы можете использовать учетную запись демонстрационного пользователя (логин guest@taipit.ru и пароль guest). 

![Установка taipit](images/setup-2.jpg)

Если вы ввели правильно логин и пароль, то появится сообщение об успешном окончании настройки.

![Установка taipit](images/setup-3.jpg)

Вы можете подключить сразу несколько учетных записей, в каждой из которых может быть несколько счетчиков.

![Установка taipit](images/setup-4.jpg)

Щелкнув на одну из них можно посмотреть устройства ли объекты созданные для этой учетной записи.

![Установка taipit](images/setup-5.jpg)

Устройством будет каждый отдельный зарегистрированный счетчик.

![Установка taipit](images/setup-6.jpg)

Объекты для каждого устройства

![Установка taipit](images/setup-7.jpg)

Доступны следующие объекты:
 - Активная энергия (общая потребленная энергия)
 - Активная энергия T1 (можно отключить если не используется двух тарифный план)
 - Активная энергия T2 (можно отключить если не используется двух тарифный план)
 - Активная энергия T3 (можно отключить если не используется трех тарифный план)
 - Напряжение
 - Ток
 - Коэффициент мощности (cos φ), при наличии
 - Серийный номер счетчика
 - MAC адрес модуля Wi-Fi
 - Уровень сигнала модуля Wi-Fi
 - Кнопка для немедленного обновления информации

Общий вид устройства в Home Assistant

![Установка taipit](images/setup-8.jpg)

Устройство можно подключить в панель Энергия, для отслеживания расхода ресурсов и их стоимости. 

![Установка taipit](images/setup-9.jpg)


# Возникли проблемы?

Включите ведение журнала отладки, поместив следующие инструкции в файл configuration.yaml:
```yaml
logger:
  default: warning
  logs:
    custom_components.taipit: debug
    aiotaipit: debug

```
После возникновения проблемы, пожалуйста, найдите проблему в журнале (/config/home-assistant.log) и создайте [запрос на исправление](https://github.com/lizardsystems/hass-taipit/issues).

# Дополнительная информация

Эта интеграция использует API https://cloud.meters.taipit.ru/.
