```
# ❌ Duplicates detected within requested policy
  ## Full 5-tuple rule duplicate within requested policy
    ### Duplicate detected between requested policy rule X and rule Y
      #### Requested policy rule X

      #### Requested policy rule Y
  ## Per-IP 5-tuple duplicate within requested policy
    ### Duplicate detected between requested policy rule X and rule Y
      #### Requested policy rule X

      #### Requested policy rule Y
  ## Duplicate IPs within a single rule
    ### Duplicate detected within requested policy rule X

# ❌ Duplicates detected between requested and existing policy
  ## Full 5-tuple duplicate between requested and existing policy
    ### Duplicate detected betweeen requested policy rule X and existing policy rule Y
      #### Requested policy rule X

      #### Existing policy rule Y
  ## Per-IP 5-tuple duplicates across files
    ### Duplicate detected between requested policy rule X and existing policy rule Y
      #### Requested policy rule X

      #### Existing policy rule Y
```




real with spacing
```
```
# ❌ Duplicates detected within requested policy

## Full 5-tuple rule duplicate within requested policy

### Duplicate detected between requested policy rule X and rule Y

#### Requested policy rule X

#### Requested policy rule Y

### Duplicate detected between requested policy rule Y and rule Z

#### Requested policy rule Y

#### Requested policy rule Z

## Per-IP 5-tuple duplicate within requested policy

### Duplicate detected between requested policy rule X and rule Y

#### Requested policy rule X

#### Requested policy rule Y

### Duplicate detected between requested policy rule Y and rule Z

#### Requested policy rule Y

#### Requested policy rule Z

## Duplicate IPs within a single rule

### Duplicate detected within requested policy rule X

### Duplicate detected within requested policy rule Y

# ❌ Duplicates detected between requested and existing policy

## Full 5-tuple duplicate between requested and existing policy

### Duplicate detected betweeen requested policy rule X and existing policy rule Y

#### Requested policy rule X

#### Existing policy rule Y

### Duplicate detected betweeen requested policy rule Y and existing policy rule Z

#### Requested policy rule Y

#### Existing policy rule Z

## Per-IP 5-tuple duplicates across files

### Duplicate detected between requested policy rule X and existing policy rule Y

#### Requested policy rule X
 
#### Existing policy rule Y

### Duplicate detected between requested policy rule Y and existing policy rule Z

#### Requested policy rule Y
 
#### Existing policy rule Z

```
```


# ❌ Duplicates detected within requested policy

## Full 5-tuple rule duplicate within requested policy

### Duplicate detected between requested policy rule X and rule Y
```yaml
    - request_id: RQ-001
      source:
        ips:
>>          - 10.1.1.1/32
>>          - 10.2.2.2/32
>>      protocol: tcp
>>      port: 443
>>      appid: ssl
>>      url: api.example.com

    - request_id: RQ-002
      source:
        ips:
>>          - 10.2.2.2/32
>>          - 10.1.1.1/32
>>      protocol: tcp
>>      port: 443
>>      appid: ssl
>>      url: api.example.com
```

## Per-IP 5-tuple duplicate within requested policy

### Duplicate detected between requested policy rule X and rule Y

```yaml
  - request_id: RQ-003
    source:
      ips: 
>>      - 10.3.3.3/32
        - 10.4.4.4/32
  protocol: tcp
  port: 100
  appid: app100
  url: foo.example.com

  - request_id: RQ-004
    source:
      ips: 
>>      - 10.3.3.3/32
        - 10.5.5.5/32
  protocol: TCP
  port: 100
  appid: APP100
  url: FOO.EXAMPLE.COM
```

## Duplicate IPs within a single rule

### Duplicate detected within requested policy rule X

```yaml
  - request_id: RQ-005
    source:
      ips: 
>>      - 10.6.6.6/32
>>      - 10.6.6.6/32
    protocol: tcp
    port: 200
    appid: dupip
    url: bar.example.com
```

# ❌ Duplicates detected between requested and existing policy

## Full 5-tuple duplicate between requested and existing policy

### Duplicate detected betweeen requested policy rule X and existing policy rule Y

```yaml
  - request_id: RQ-007
    source:
      ips: 
>>      - 10.8.8.8/32
>>      - 10.9.9.9/32
>>  protocol: tcp
>>  port: 300
>>  appid: existapp
>>  url: exist.example.com
```


```yaml
  - request_id: EXIST-001
    source:
      ips:
>>      - 10.9.9.9/32
>>      - 10.8.8.8/32
>>  protocol: TCP
>>  port: '300'
>>  appid: EXISTAPP
>>  url: EXIST.EXAMPLE.COM
```

## Per-IP 5-tuple duplicates across files

### Duplicate detected between requested policy rule X and existing policy rule Y

```yaml
  - request_id: RQ-003
    source:
      ips:
        - 10.3.3.3/32
>>      - 10.4.4.4/32
    protocol: tcp
    port: 100
    appid: app100
    url: foo.example.com
```

```yaml
  - request_id: EXIST-002
    source:
      ips:
>>      - 10.4.4.4/32
        - 10.10.10.10/32
    protocol: tcp
    port: 100
    appid: app100
    url: foo.example.com
```
